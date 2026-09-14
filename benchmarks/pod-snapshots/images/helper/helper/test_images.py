import shlex
import subprocess
from unittest.mock import MagicMock, patch

import pytest

import images


class TestCreateImageHelper:
    def test_gcp(self):
        helper = images.create_image_helper("gcp")
        assert isinstance(helper, images.GCPImageHelper)
        assert helper._get_token_cli_command() == "gcloud auth print-access-token"

    def test_aws(self):
        helper = images.create_image_helper("aws")
        assert isinstance(helper, images.AWSImageHelper)
        assert helper._get_token_cli_command() == "aws ecr get-login-password"

    def test_azure(self, tmp_path, monkeypatch):
        token_file = tmp_path / "federated-token"
        token_file.write_text("federated-token-value")
        monkeypatch.setenv("AZURE_ACR_REGISTRY_NAME", "my-registry")
        monkeypatch.setenv("AZURE_FEDERATED_TOKEN_FILE", str(token_file))
        monkeypatch.setenv("AZURE_CLIENT_ID", "client-id")
        monkeypatch.setenv("AZURE_TENANT_ID", "tenant-id")

        with patch("images.subprocess.run") as mock_run:
            helper = images.create_image_helper("azure")

        assert isinstance(helper, images.AzureImageHelper)
        assert helper.registry_name == "my-registry"
        mock_run.assert_called_once()  # the az login call inside login_azure()

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown cloud provider type"):
            images.create_image_helper("oracle-cloud")


class TestAzureTokenCommand:
    def test_quotes_registry_name(self):
        # shlex.quote() wraps the value in quotes rather than stripping it,
        # so the meaningful assertion is that the *quoted* form is what
        # lands in the command -- if quoting were ever dropped, this exact
        # substring would no longer match.
        registry_name = "my registry; rm -rf /"
        helper = images.AzureImageHelper(registry_name=registry_name)
        cmd = helper._get_token_cli_command()
        assert shlex.quote(registry_name) in cmd


class TestGetPassword:
    def test_returns_stripped_stdout(self):
        helper = images.GCPImageHelper()
        completed = MagicMock(stdout=b"  token-value\n")
        with patch("images.subprocess.run", return_value=completed) as mock_run:
            password = helper._get_password()
        assert password == "token-value"
        mock_run.assert_called_once_with(
            "gcloud auth print-access-token",
            shell=True,
            check=True,
            capture_output=True,
        )

    def test_propagates_called_process_error(self):
        helper = images.GCPImageHelper()
        with patch(
            "images.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "cmd", stderr=b"boom"),
        ):
            with pytest.raises(subprocess.CalledProcessError):
                helper._get_password()


class TestPullImagesWithCtr:
    def test_quotes_image_names_with_shell_metacharacters(self):
        helper = images.GCPImageHelper()
        malicious_image = "gcr.io/foo/bar:latest; rm -rf / #"
        with patch.object(images.ImageHelper, "_get_password", return_value="tok"), patch(
            "images.subprocess.run"
        ) as mock_run:
            helper.pull_images_with_ctr([malicious_image])

        mock_run.assert_called_once()
        cmd = mock_run.call_args.args[0]
        assert mock_run.call_args.kwargs["shell"] is True
        # If quoting were ever dropped, the image name would land in the
        # command unquoted and this substring match would fail.
        assert shlex.quote(malicious_image) in cmd
        assert mock_run.call_args.kwargs["env"]["CTR_CREDENTIALS"] == "oauth2accesstoken:tok"

    def test_pulls_each_image_in_the_list(self):
        helper = images.GCPImageHelper()
        with patch.object(images.ImageHelper, "_get_password", return_value="tok"), patch(
            "images.subprocess.run"
        ) as mock_run:
            helper.pull_images_with_ctr(["img-a", "img-b"])
        assert mock_run.call_count == 2


class TestCopyPublicImagesToRegistry:
    def test_quotes_src_and_dest(self):
        helper = images.AWSImageHelper()
        entry = {
            "src": "docker.io/foo; touch /tmp/pwned",
            "dest": "123.dkr.ecr.example/bar`whoami`",
        }
        with patch.object(images.ImageHelper, "_get_password", return_value="tok"), patch(
            "images.subprocess.run"
        ) as mock_run:
            helper.copy_public_images_to_registry([entry])

        cmd = mock_run.call_args.args[0]
        assert shlex.quote(entry["src"]) in cmd
        assert shlex.quote(entry["dest"]) in cmd
        assert mock_run.call_args.kwargs["env"]["CTR_CREDENTIALS"] == "AWS:tok"


class TestLoginAzure:
    def test_builds_env_from_expected_variables(self, tmp_path, monkeypatch):
        token_file = tmp_path / "federated-token"
        token_file.write_text("federated-token-value")
        monkeypatch.setenv("AZURE_FEDERATED_TOKEN_FILE", str(token_file))
        monkeypatch.setenv("AZURE_CLIENT_ID", "client-id")
        monkeypatch.setenv("AZURE_TENANT_ID", "tenant-id")

        with patch("images.subprocess.run") as mock_run:
            images.login_azure()

        mock_run.assert_called_once()
        assert mock_run.call_args.kwargs["env"] == {
            "FEDERATED_TOKEN": "federated-token-value",
            "AZURE_CLIENT_ID": "client-id",
            "AZURE_TENANT_ID": "tenant-id",
        }
