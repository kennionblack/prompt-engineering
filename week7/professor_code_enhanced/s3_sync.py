"""
Simple S3 sync for skills directory.
Syncs skills between local ./agent/skills/ and S3 bucket.
"""

import os
import boto3
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class S3SkillSync:
    """Syncs skills with S3 bucket"""

    def __init__(self, skills_dir: str = "./agent/skills"):
        self.skills_dir = Path(skills_dir)
        self.bucket_name = os.getenv("AWS_S3_BUCKET_NAME")

        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

    def download_all_skills(self):
        """Download all skills from S3 to local directory"""
        print("📥 Downloading skills from S3...")

        # Create skills directory if it doesn't exist
        self.skills_dir.mkdir(parents=True, exist_ok=True)

        try:
            # List all objects in bucket
            response = self.s3.list_objects_v2(Bucket=self.bucket_name)

            if "Contents" not in response:
                print("✅ No skills in S3 bucket")
                return

            count = 0
            for obj in response["Contents"]:
                key = obj["Key"]
                local_path = self.skills_dir / key

                # Create parent directories
                local_path.parent.mkdir(parents=True, exist_ok=True)

                # Download file
                self.s3.download_file(self.bucket_name, key, str(local_path))
                count += 1

            print(f"✅ Downloaded {count} files from S3")

        except Exception as e:
            print(f"❌ Error downloading from S3: {e}")

    def upload_all_skills(self):
        """Upload all skills from local directory to S3"""
        print("📤 Uploading skills to S3...")

        if not self.skills_dir.exists():
            print("⚠️  Skills directory doesn't exist")
            return

        try:
            count = 0
            for file_path in self.skills_dir.rglob("*"):
                if not file_path.is_file():
                    continue

                # Skip __pycache__ and .pyc files
                if "__pycache__" in str(file_path) or file_path.suffix == ".pyc":
                    continue

                # Get relative path from skills directory
                relative_path = file_path.relative_to(self.skills_dir)
                s3_key = str(relative_path).replace(
                    "\\", "/"
                )  # Use forward slashes for S3

                # Upload file
                self.s3.upload_file(str(file_path), self.bucket_name, s3_key)
                count += 1

            print(f"✅ Uploaded {count} files to S3")

        except Exception as e:
            print(f"❌ Error uploading to S3: {e}")


def sync_from_s3():
    """Download skills from S3"""
    syncer = S3SkillSync()
    syncer.download_all_skills()


def sync_to_s3():
    """Upload skills to S3"""
    syncer = S3SkillSync()
    syncer.upload_all_skills()
