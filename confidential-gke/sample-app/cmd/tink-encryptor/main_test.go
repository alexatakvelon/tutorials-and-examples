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

import "testing"

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
			// The function splits on "/" and only keeps parts[0] and
			// parts[1], so an object path with its own "/" separators
			// (a common case for GCS, which uses them as pseudo-directory
			// separators) is silently truncated to its first segment.
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
		{
			name:       "trailing slash yields an empty object name",
			blobPath:   "gs://my-bucket/",
			wantBucket: "my-bucket",
			wantObject: "",
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
