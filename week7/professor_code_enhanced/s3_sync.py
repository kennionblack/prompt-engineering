import os
import boto3
import hashlib
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
            response = self.s3.list_objects_v2(Bucket=self.bucket_name)

            if "Contents" not in response:
                print("No skills in S3 bucket")
                return

            count = 0
            for obj in response["Contents"]:
                key = obj["Key"]
                local_path = self.skills_dir / key

                local_path.parent.mkdir(parents=True, exist_ok=True)

                self.s3.download_file(self.bucket_name, key, str(local_path))
                count += 1

            print(f"Downloaded {count} files from S3")

        except Exception as e:
            print(f"Error downloading from S3: {e}")

    def upload_all_skills(self):
        """Upload all skills from local directory to S3"""
        print("Uploading skills to S3...")

        if not self.skills_dir.exists():
            print("Skills directory doesn't exist")
            return

        try:
            count = 0
            for file_path in self.skills_dir.rglob("*"):
                if not file_path.is_file():
                    continue

                # Skip __pycache__ and .pyc files
                if "__pycache__" in str(file_path) or file_path.suffix == ".pyc":
                    continue

                relative_path = file_path.relative_to(self.skills_dir)
                s3_key = str(relative_path).replace("\\", "/")

                self.s3.upload_file(str(file_path), self.bucket_name, s3_key)
                count += 1

            print(f"Uploaded {count} files to S3")

        except Exception as e:
            print(f"Error uploading to S3: {e}")

    def list_s3_skills(self) -> set[str]:
        """Get list of skill names in S3 bucket"""
        try:
            response = self.s3.list_objects_v2(Bucket=self.bucket_name)

            if "Contents" not in response:
                return set()

            # Extract skill names (first directory level)
            skills = set()
            for obj in response["Contents"]:
                key = obj["Key"]
                if "/" in key:
                    skill_name = key.split("/")[0]
                    skills.add(skill_name)

            return skills

        except Exception as e:
            print(f"Error listing S3 skills: {e}")
            return set()

    def list_local_skills(self) -> set[str]:
        """Get list of skill names in local directory"""
        if not self.skills_dir.exists():
            return set()

        skills = set()
        for item in self.skills_dir.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                skills.add(item.name)

        return skills

    def get_deleted_skills(self) -> set[str]:
        """Get skills that exist in S3 but not locally (i.e., were deleted locally)"""
        s3_skills = self.list_s3_skills()
        local_skills = self.list_local_skills()
        return s3_skills - local_skills

    def delete_skill_from_s3(self, skill_name: str):
        """Delete all files for a specific skill from S3"""
        try:
            response = self.s3.list_objects_v2(
                Bucket=self.bucket_name, Prefix=f"{skill_name}/"
            )

            if "Contents" not in response:
                print(f"⚠️  Skill '{skill_name}' not found in S3")
                return

            objects_to_delete = [{"Key": obj["Key"]} for obj in response["Contents"]]

            if objects_to_delete:
                self.s3.delete_objects(
                    Bucket=self.bucket_name, Delete={"Objects": objects_to_delete}
                )
                print(
                    f"Deleted {len(objects_to_delete)} files for skill '{skill_name}' from S3"
                )

        except Exception as e:
            print(f"Error deleting skill '{skill_name}' from S3: {e}")

    def delete_skills_from_s3(self, skill_names: list[str]):
        """Delete multiple skills from S3"""
        for skill_name in skill_names:
            self.delete_skill_from_s3(skill_name)

    def get_skill_hash(self, skill_name: str, local: bool = True) -> str:
        """
        Calculate SHA256 hash of all files in a skill directory.

        Args:
            skill_name: Name of the skill
            local: If True, hash local files; if False, hash S3 files

        Returns:
            Hex digest of the combined file hashes (sorted for consistency)
        """
        hasher = hashlib.sha256()

        if local:
            skill_path = self.skills_dir / skill_name
            if not skill_path.exists():
                return ""

            # Get all files in sorted order for consistent hashing
            files = sorted(skill_path.rglob("*"))
            for file_path in files:
                if (
                    file_path.is_file()
                    and "__pycache__" not in str(file_path)
                    and file_path.suffix != ".pyc"
                ):
                    # Hash the relative path and content
                    rel_path = file_path.relative_to(skill_path)
                    hasher.update(str(rel_path).encode())
                    hasher.update(file_path.read_bytes())
        else:
            # Hash S3 files
            try:
                response = self.s3.list_objects_v2(
                    Bucket=self.bucket_name, Prefix=f"{skill_name}/"
                )

                if "Contents" not in response:
                    return ""

                # Sort by key for consistent hashing
                objects = sorted(response["Contents"], key=lambda x: x["Key"])

                for obj in objects:
                    key = obj["Key"]
                    if "__pycache__" in key or key.endswith(".pyc"):
                        continue

                    # Hash the key
                    hasher.update(key.encode())

                    # Download and hash the content
                    obj_response = self.s3.get_object(Bucket=self.bucket_name, Key=key)
                    hasher.update(obj_response["Body"].read())

            except Exception as e:
                print(f"Error hashing S3 skill '{skill_name}': {e}")
                return ""

        return hasher.hexdigest()

    def get_modified_skills(self) -> dict[str, tuple[str, str]]:
        """
        Get skills that exist in both local and S3 but have different content.

        Returns:
            Dict mapping skill_name -> (local_hash, s3_hash) for modified skills
        """
        s3_skills = self.list_s3_skills()
        local_skills = self.list_local_skills()

        common_skills = s3_skills & local_skills

        modified = {}
        for skill_name in common_skills:
            local_hash = self.get_skill_hash(skill_name, local=True)
            s3_hash = self.get_skill_hash(skill_name, local=False)

            if local_hash != s3_hash and local_hash and s3_hash:
                modified[skill_name] = (local_hash, s3_hash)

        return modified


def sync_from_s3():
    """Download skills from S3"""
    syncer = S3SkillSync()
    syncer.download_all_skills()


def sync_to_s3():
    """Upload skills to S3"""
    syncer = S3SkillSync()
    syncer.upload_all_skills()
