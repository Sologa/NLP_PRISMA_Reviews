# QA-First Experiment Prompt Templates

All prompts in this bundle are externalized template files.

Usage pattern:

1. Choose the template listed in `prompt_manifest.yaml`.
2. Load the template file from disk.
3. Fill placeholders with a JSON or YAML context.
4. Send the rendered prompt to the model runner.

Do not hardcode these prompt bodies into `.py` or notebook string constants.
