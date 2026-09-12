import importlib.util
from importlib.machinery import SourceFileLoader
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / ".local/bin/git-ssh-keygen"
spec = importlib.util.spec_from_loader("signing", SourceFileLoader("signing", str(SCRIPT)))
signing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(signing)


STUB = r'''
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

root = Path(os.environ["STUB_ROOT"])
name = Path(sys.argv[0]).name
def log(event, **fields):
    with (root / "calls").open("a") as stream:
        stream.write(json.dumps(dict(event=event, **fields)) + "\n")

if name == "brew":
    print(root)
elif name == "ssh-keygen":
    args = sys.argv[1:]
    if "-l" in args:
        if os.environ.get("BAD_FINGERPRINT"):
            sys.exit(1)
        key = Path(args[args.index("-f") + 1]).read_bytes()
        fp = base64.b64encode(hashlib.sha256(key).digest()).decode().rstrip("=")
        print("256 SHA256:" + fp + " test-key (ED25519-SK)")
    elif "sign" in args:
        log("sign", args=args, agent_socket=os.environ.get("SSH_AUTH_SOCK"))
        data = sys.stdin.buffer.read()
        for hint, prompt in json.loads(os.environ.get("PROMPTS", '[["none", "Confirm user presence"], ["", "Enter PIN for ED25519-SK key: "]]')):
            env = dict(os.environ)
            env.pop("SSH_ASKPASS_PROMPT", None)
            if hint:
                env["SSH_ASKPASS_PROMPT"] = hint
            result = subprocess.run([env["SSH_ASKPASS"], prompt], env=env, capture_output=True)
            sys.stderr.buffer.write(result.stderr)
            if result.returncode:
                sys.exit(9)
            if hint in ("none", "confirm"):
                assert result.stdout == b""
            else:
                assert result.stdout == b"test-pin%+value\n", "incorrect secret decoding"
        sys.stdout.buffer.write(b"signature:" + data)
        sys.exit(int(os.environ.get("SIGN_EXIT", "0")))
    else:
        log("passthrough", args=args, agent_socket=os.environ.get("SSH_AUTH_SOCK"))
        sys.stdout.buffer.write(sys.stdin.buffer.read())
        sys.exit(7)
elif name == "gpg-connect-agent":
    assert sys.argv[1:] == ["--no-history"]
    for command in sys.stdin.read().splitlines():
        if command == "/bye":
            break
        fields = command.split()
        log("agent", command=command, tty=os.environ.get("GPG_TTY"), display=os.environ.get("DISPLAY"),
            wayland=os.environ.get("WAYLAND_DISPLAY"), agent_socket=os.environ.get("SSH_AUTH_SOCK"))
        cache_path = root / "cache"
        cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
        if fields[0] == "CLEAR_PASSPHRASE":
            cache.pop(fields[1], None)
            cache_path.write_text(json.dumps(cache))
            print("OK")
        elif fields[0] == "GET_CONFIRMATION":
            print("ERR 99 cancelled" if os.environ.get("CANCEL") else "OK")
        else:
            assert fields[0] == "GET_PASSPHRASE"
            if os.environ.get("CANCEL"):
                print("ERR 99 cancelled")
                continue
            cache_id = fields[2]
            now = int(os.environ.get("STUB_TIME", "0"))
            if cache_id == "X" or cache_id not in cache or now - cache[cache_id] >= 600:
                log("dialog")
            if cache_id != "X":
                cache[cache_id] = now
                cache_path.write_text(json.dumps(cache))
            print("D test-pin%25+value\nOK")
elif name.startswith("pinentry"):
    print("OK pinentry ready")
    for command in sys.stdin.read().splitlines():
        log("pinentry", command=command)
        if command == "GETPIN":
            print("D test-pin%25+value")
        print("ERR 99 cancelled" if command in ("GETPIN", "CONFIRM") and os.environ.get("CANCEL") else "OK")
'''


class SigningTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="git signing tests ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for name in ("brew", "ssh-keygen", "gpg-connect-agent", "pinentry-mac"):
            command = self.bin / name
            command.write_text("#!" + sys.executable + "\n" + STUB)
            command.chmod(0o755)
        self.key = self.root / "key handle"
        self.key.write_text("fake public key one")
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith("GIT_SSH_KEYGEN_") and key not in ("DISPLAY", "WAYLAND_DISPLAY", "SSH_ASKPASS_PROMPT")}
        self.env.update(STUB_ROOT=str(self.root), PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
                        SSH_AUTH_SOCK="must-not-be-used", GIT_SSH_KEYGEN_TRACE="1")

    def calls(self, event):
        path = self.root / "calls"
        return [item for line in path.read_text().splitlines()
                for item in [json.loads(line)] if item["event"] == event] if path.exists() else []

    def sign(self, expected=0, **env):
        result = subprocess.run([sys.executable, str(SCRIPT), "-Y", "sign", "-n", "git", "-f", str(self.key)],
                                input=b"payload-must-not-be-traced", env=dict(self.env, **env), capture_output=True)
        self.assertEqual(result.returncode, expected, result.stderr.decode())
        self.assertNotIn(b"test-pin", result.stderr)
        self.assertNotIn(b"payload-must-not-be-traced", result.stderr)
        return result

    def test_reuses_agent_cache_and_prompts_again_after_expiry(self):
        first = self.sign()
        second = self.sign(STUB_TIME="100")
        self.assertEqual(first.stdout, b"signature:payload-must-not-be-traced")
        self.assertEqual(second.stdout, first.stdout)
        self.assertEqual(len(self.calls("dialog")), 1)
        self.assertEqual(len(self.calls("agent")), 2)
        self.sign(STUB_TIME="701")
        self.assertEqual(len(self.calls("dialog")), 2)
        self.assertTrue(all(call["agent_socket"] is None for call in self.calls("agent") + self.calls("sign")))
        self.assertIn(b"prompt=notification hint=none", first.stderr)
        self.assertIn(b"prompt=pin hint=secret", first.stderr)
        ids = re.findall(rb"git-ssh-keygen\[([0-9a-f]{12})\]", first.stderr)
        self.assertEqual(len(set(ids)), 1)
        self.assertNotIn(ids[0], second.stderr)

    def test_distinct_keys_have_separate_cache_ids(self):
        self.sign()
        first = self.calls("agent")[-1]["command"].split()[2]
        self.key.write_text("fake public key two")
        self.sign()
        second = self.calls("agent")[-1]["command"].split()[2]
        self.assertNotEqual(first, second)
        self.assertLessEqual(len(first), 50)
        self.assertEqual(len(self.calls("dialog")), 2)

    def test_passphrases_and_unknown_prompts_are_uncached_and_accurately_labelled(self):
        prompts = json.dumps([["", "Enter passphrase for key '/key': "], ["", "Unknown secret prompt"]])
        self.sign(PROMPTS=prompts)
        commands = [call["command"] for call in self.calls("agent")]
        self.assertIn(" X X Passphrase%3A ", commands[0])
        self.assertIn(" X X Secret%3A ", commands[1])
        self.assertFalse((self.root / "cache").exists())

    def test_confirmation_never_requests_a_secret(self):
        self.sign(PROMPTS=json.dumps([["confirm", "Allow signing?"]]))
        self.assertEqual(self.calls("agent")[0]["command"], "GET_CONFIRMATION Allow%20signing%3F")
        self.assertEqual(self.calls("dialog"), [])

    def test_failure_clears_only_this_keys_cache_without_retrying(self):
        self.sign()
        other_key_id = self.calls("agent")[-1]["command"].split()[2]
        self.key.write_text("fake public key two")
        self.sign(expected=5, SIGN_EXIT="5")
        self.assertEqual(len(self.calls("sign")), 2)
        self.assertTrue(self.calls("agent")[-1]["command"].startswith("CLEAR_PASSPHRASE git-ssh-pin:"))
        self.assertEqual(set(json.loads((self.root / "cache").read_text())), {other_key_id})
        self.sign()
        self.assertEqual(len(self.calls("dialog")), 3)

    def test_cancellation_stops_without_fallback_or_retry(self):
        self.sign(expected=9, CANCEL="1")
        self.assertEqual(len(self.calls("sign")), 1)
        self.assertEqual(self.calls("pinentry"), [])
        self.assertEqual(self.calls("dialog"), [])

    def test_unknown_key_fingerprint_disables_caching(self):
        self.sign(BAD_FINGERPRINT="1")
        self.assertIn("--data X X PIN%3A", self.calls("agent")[0]["command"])

    def test_display_and_terminal_environment_is_forwarded(self):
        self.sign(DISPLAY=":test", WAYLAND_DISPLAY="wayland-test", GPG_TTY="/dev/test-tty")
        call = self.calls("agent")[0]
        self.assertEqual(call["display"], ":test")
        self.assertEqual(call["wayland"], "wayland-test")
        self.assertEqual(call["tty"], "/dev/test-tty")

    def test_non_signing_operations_preserve_arguments_io_and_status(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "-Y", "verify", "-n", "git"],
                                input=b"test input", env=self.env, capture_output=True)
        self.assertEqual(result.returncode, 7)
        self.assertEqual(result.stdout, b"test input")
        self.assertEqual(self.calls("agent"), [])
        self.assertEqual(self.calls("passthrough")[0]["args"], ["-Y", "verify", "-n", "git"])

    def test_fallback_pinentry_and_notification(self):
        env = dict(self.env, GIT_SSH_KEYGEN_ASKPASS="1", GIT_SSH_KEYGEN_BACKEND="pinentry",
                   GIT_SSH_KEYGEN_PROMPT_PROGRAM=str(self.bin / "pinentry-mac"))
        for hint, prompt, output in (("none", "Touch", b""), ("confirm", "Allow?", b""),
                                     ("", "Enter PIN for ED25519-SK key: ", b"test-pin%+value\n")):
            result = subprocess.run([sys.executable, str(SCRIPT), prompt],
                                    env=dict(env, SSH_ASKPASS_PROMPT=hint), capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, output)
        self.assertEqual(sum(call["command"] == "GETPIN" for call in self.calls("pinentry")), 1)


class ProtocolTests(unittest.TestCase):
    def test_empty_secret_fails_without_writing_an_askpass_response(self):
        with mock.patch.dict(os.environ, {
            signing.PREFIX + "BACKEND": "agent", signing.PREFIX + "PROMPT_PROGRAM": "/agent",
        }, clear=True), mock.patch.object(signing, "assuan", return_value=b""), \
                mock.patch.object(signing.sys, "stdout") as output:
            with self.assertRaises(signing.PromptError):
                signing.askpass("Enter PIN for ED25519-SK key: ")
            output.buffer.write.assert_not_called()

    def test_protocol_errors_never_return_partial_secrets(self):
        responses = (b"D test-secret\nERR 99 cancelled\n", b"D test-secret\n",
                     b"D test-secret\nOK\nOK\n", b"D invalid%ZZ\nOK\n",
                     b"D invalid%0Anewline\nOK\n", b"INQUIRE unexpected\nOK\n")
        for output in responses:
            with self.subTest(output=output):
                with mock.patch.object(signing.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, output, b"")):
                    with self.assertRaises(signing.PromptError) as error:
                        signing.assuan("agent", ["GET_PASSPHRASE"], agent=True)
                    self.assertNotIn("test-secret", str(error.exception))

    def test_multiline_data_is_decoded_once_and_prompt_is_escaped(self):
        response = subprocess.CompletedProcess([], 0, b"S info\nD test%25\nD 2B+value\nOK\n", b"")
        with mock.patch.object(signing.subprocess, "run", return_value=response):
            self.assertEqual(signing.assuan("agent", ["GET_PASSPHRASE"], agent=True), b"test%2B+value")
        self.assertEqual(signing.escape("a\nb%+ c"), "a%0Ab%25%2B%20c")

    def test_prompt_backend_selection_without_gnupg(self):
        for platform, display, available, expected in (
            ("darwin", {}, {"pinentry-mac": "/pinentry"}, "pinentry"),
            ("linux", {"DISPLAY": ":0"}, {"pinentry-gnome3": "/pinentry"}, "pinentry"),
            ("linux", {}, {}, None),
            ("darwin", {}, {"gpg-connect-agent": "/agent"}, "agent"),
        ):
            with self.subTest(platform=platform, expected=expected):
                with mock.patch.dict(os.environ, display, clear=True), mock.patch.object(signing.sys, "platform", platform), \
                        mock.patch.object(signing.shutil, "which", side_effect=available.get), \
                        mock.patch.object(signing.os, "isatty", return_value=False):
                    signing.configure_prompt()
                    self.assertEqual(os.environ.get(signing.PREFIX + "BACKEND"), expected)
                    self.assertEqual(os.environ.get("SSH_ASKPASS_REQUIRE"), "force" if expected else None)

    def test_current_terminal_replaces_stale_tty_setting(self):
        with mock.patch.dict(os.environ, {"GPG_TTY": "/dev/stale"}, clear=True), \
                mock.patch.object(signing.shutil, "which", return_value="/agent"), \
                mock.patch.object(signing.os, "isatty", side_effect=lambda fd: fd == 2), \
                mock.patch.object(signing.os, "ttyname", return_value="/dev/pts/123"):
            signing.configure_prompt()
            self.assertEqual(os.environ["GPG_TTY"], "/dev/pts/123")


@unittest.skipUnless(shutil.which("gpg-connect-agent") and shutil.which("gpgconf"), "requires GnuPG")
class AgentIntegrationTests(unittest.TestCase):
    def test_real_agent_caches_expires_and_clears_test_pin(self):
        # A separate agent and fake pinentry never use the user's keys or cache.
        with tempfile.TemporaryDirectory(prefix="signing-agent-", dir="/tmp") as directory:
            root = Path(directory)
            pinentry = root / "pinentry"
            calls = root / "dialogs"
            pinentry.write_text(
                "#!" + sys.executable + "\nimport sys\nfrom pathlib import Path\n"
                "print('OK ready', flush=True)\n"
                "for line in sys.stdin:\n"
                "    if line.strip() == 'GETPIN':\n"
                "        with Path({!r}).open('a') as stream:\n"
                "            stream.write('dialog\\n')\n"
                "        print('D test-pin%25+value', flush=True)\n"
                "    print('OK', flush=True)\n"
                "    if line.strip() == 'BYE':\n"
                "        break\n".format(str(calls))
            )
            pinentry.chmod(0o755)
            (root / "gpg-agent.conf").write_text(
                "pinentry-program {}\ndefault-cache-ttl 1\nmax-cache-ttl 1\nno-allow-external-cache\n".format(pinentry)
            )
            agent = shutil.which("gpg-connect-agent")
            with mock.patch.dict(os.environ, {"GNUPGHOME": directory}):
                try:
                    command = "GET_PASSPHRASE --data git-ssh-pin:test X PIN Test"
                    for _ in range(2):
                        self.assertEqual(signing.assuan(agent, [command], agent=True), b"test-pin%+value")
                    self.assertEqual(calls.read_text().splitlines(), ["dialog"])
                    time.sleep(1.2)
                    signing.assuan(agent, [command], agent=True)
                    self.assertEqual(len(calls.read_text().splitlines()), 2)
                    signing.assuan(agent, ["CLEAR_PASSPHRASE git-ssh-pin:test"], agent=True)
                    signing.assuan(agent, [command], agent=True)
                    self.assertEqual(len(calls.read_text().splitlines()), 3)
                finally:
                    subprocess.run([shutil.which("gpgconf"), "--homedir", directory, "--kill", "gpg-agent"],
                                   capture_output=True, check=True)


if __name__ == "__main__":
    unittest.main()
