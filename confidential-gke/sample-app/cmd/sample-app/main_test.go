// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package main

import (
	"testing"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

func TestGetBucketAndObject(t *testing.T) {
	tests := []struct {
		name       string
		blobPath   string
		wantBucket string
		wantObject string
		wantErr    bool
	}{
		{
			name:       "simple bucket and object",
			blobPath:   "gs://my-bucket/my-object.txt",
			wantBucket: "my-bucket",
			wantObject: "my-object.txt",
		},
		{
			// See the identical helper in cmd/tink-encryptor: nested object
			// paths are silently truncated to their first "/"-delimited
			// segment.
			name:       "nested object path is silently truncated to its first segment",
			blobPath:   "gs://my-bucket/path/to/object.txt",
			wantBucket: "my-bucket",
			wantObject: "path",
		},
		{
			name:     "missing gs:// prefix",
			blobPath: "my-bucket/my-object.txt",
			wantErr:  true,
		},
		{
			name:     "bucket only, no object segment",
			blobPath: "gs://my-bucket",
			wantErr:  true,
		},
		{
			name:     "empty path",
			blobPath: "",
			wantErr:  true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			bucket, object, err := getBucketAndObject(tt.blobPath)
			if tt.wantErr {
				if err == nil {
					t.Fatalf("getBucketAndObject(%q) = nil error, want error", tt.blobPath)
				}
				return
			}
			if err != nil {
				t.Fatalf("getBucketAndObject(%q) unexpected error: %v", tt.blobPath, err)
			}
			if bucket != tt.wantBucket || object != tt.wantObject {
				t.Errorf("getBucketAndObject(%q) = (%q, %q), want (%q, %q)", tt.blobPath, bucket, object, tt.wantBucket, tt.wantObject)
			}
		})
	}
}

// resetFlags saves the current value of every flag validateFlags checks and
// returns a func that restores them, since they're package-level vars shared
// across the whole test binary.
func resetFlags(t *testing.T) func() {
	t.Helper()
	origKek, origBlob, origProj, origWip, origProvider := *kekURI, *gcsBlobPath, *projectNumber, *wipName, *wipProvider
	return func() {
		*kekURI, *gcsBlobPath, *projectNumber, *wipName, *wipProvider = origKek, origBlob, origProj, origWip, origProvider
	}
}

func TestValidateFlags(t *testing.T) {
	defer resetFlags(t)()

	setAll := func(kek, blob, proj, wip, provider string) {
		*kekURI, *gcsBlobPath, *projectNumber, *wipName, *wipProvider = kek, blob, proj, wip, provider
	}

	t.Run("all flags set", func(t *testing.T) {
		setAll("kek", "gs://b/o", "123", "wip", "provider")
		if err := validateFlags(); err != nil {
			t.Errorf("validateFlags() = %v, want nil", err)
		}
	})

	missing := []struct {
		name string
		set  func()
	}{
		{"missing kek_uri", func() { setAll("", "gs://b/o", "123", "wip", "provider") }},
		{"missing gcs_blob_path", func() { setAll("kek", "", "123", "wip", "provider") }},
		{"missing project_number", func() { setAll("kek", "gs://b/o", "", "wip", "provider") }},
		{"missing wip_name", func() { setAll("kek", "gs://b/o", "123", "", "provider") }},
		{"missing wip_provider", func() { setAll("kek", "gs://b/o", "123", "wip", "") }},
	}
	for _, tt := range missing {
		t.Run(tt.name, func(t *testing.T) {
			tt.set()
			if err := validateFlags(); err == nil {
				t.Errorf("validateFlags() = nil, want error")
			}
		})
	}
}

func TestDecodeJWT(t *testing.T) {
	t.Run("valid token exposes its expiration", func(t *testing.T) {
		want := time.Now().Add(5 * time.Minute).Truncate(time.Second)
		claims := jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(want),
		}
		signed, err := jwt.NewWithClaims(jwt.SigningMethodHS256, claims).SignedString([]byte("test-secret"))
		if err != nil {
			t.Fatalf("failed to build test token: %v", err)
		}

		tok, err := decodeJWT([]byte(signed))
		if err != nil {
			t.Fatalf("decodeJWT() unexpected error: %v", err)
		}
		got, err := tok.Claims.GetExpirationTime()
		if err != nil {
			t.Fatalf("GetExpirationTime() unexpected error: %v", err)
		}
		if got == nil || !got.Time.Equal(want) {
			t.Errorf("expiration = %v, want %v", got, want)
		}
	})

	t.Run("malformed token errors", func(t *testing.T) {
		if _, err := decodeJWT([]byte("not-a-jwt")); err == nil {
			t.Error("decodeJWT(malformed) = nil error, want error")
		}
	})

	t.Run("empty token errors", func(t *testing.T) {
		if _, err := decodeJWT([]byte("")); err == nil {
			t.Error("decodeJWT(empty) = nil error, want error")
		}
	})
}
