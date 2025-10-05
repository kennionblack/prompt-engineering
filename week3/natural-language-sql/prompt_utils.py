from pathlib import Path


class PromptTextInsertion:
    @staticmethod
    def replace_keyword(original_text: str, keyword: str, replacement: str) -> str:
        """Replaces all occurrences of ${keyword} in original_text with replacement."""
        return original_text.replace(f"${{{keyword}}}", replacement)

    @staticmethod
    def replace_keywords(original_text: str, replacements: dict[str, str]) -> str:
        """Replaces all occurrences of ${keyword} in original_text with replacement for each key, value pair in replacements."""
        for key, value in replacements.items():
            original_text = PromptTextInsertion.replace_keyword(original_text, key, value)
        return original_text

    @staticmethod
    def populate_prompt(prompt_path: Path, replacements: dict[str, str]) -> str:
        """Reads the prompt file at prompt_path and replaces all occurrences of ${keyword} in the prompt with replacement for each key, value pair in replacements."""
        try:
            prompt_text = Path(prompt_path).read_text()
            return PromptTextInsertion.replace_keywords(prompt_text, replacements)
        except FileNotFoundError:
            print(f"File {prompt_path} does not exist at the specified location")
            return ""
