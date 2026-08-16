import unittest
from sattva.agent.prompts import build_system_prompt
from sattva.agent.engine import _extract_fallback_tool_calls, SattvaAgent
from sattva.config import Config


class TestAgentPromptsAndEngine(unittest.TestCase):
    def test_build_system_prompt_no_keyerror(self):
        prompt = build_system_prompt(
            workspace_path="D:/test-workspace",
            tools_doc="[list_directory: Lists files in a directory]",
            include_xml_fallback=True,
        )
        self.assertIn("D:/test-workspace", prompt)
        self.assertIn("```tool_call", prompt)
        self.assertIn("list_directory", prompt)

    def test_extract_fallback_tool_calls_json_block(self):
        text = '''Here is the tool call:
```json
{
  "name": "list_directory",
  "arguments": {"dir_path": "."}
}
```
'''
        calls = _extract_fallback_tool_calls(text)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["function"]["name"], "list_directory")
        self.assertEqual(calls[0]["function"]["arguments"]["dir_path"], ".")

    def test_extract_fallback_tool_calls_xml(self):
        text = '<tool_call>{"name": "read_file", "arguments": {"file_path": "test.py"}}</tool_call>'
        calls = _extract_fallback_tool_calls(text)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["function"]["name"], "read_file")
        self.assertEqual(calls[0]["function"]["arguments"]["file_path"], "test.py")

    def test_extract_fallback_tool_calls_relaxed_json(self):
        text = '''```tool_call
{
  "name": "scan_codebase",
  "arguments": {
    "target_dir": ".",
  },
}
```'''
        calls = _extract_fallback_tool_calls(text)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["function"]["name"], "scan_codebase")


if __name__ == "__main__":
    unittest.main()
