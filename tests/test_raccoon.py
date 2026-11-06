#!/usr/bin/env python3
"""
disk-raccoon 自动化测试套件
验证规则结构、绝对物理熔断、敏感机密二级熔断、符号链接不穿透、多维度精准目标选择器与并发排他锁。
"""

import os
import sys
import shutil
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts")))
import importlib
fast_scan = importlib.import_module("fast-scan")

class TestDiskRaccoon(unittest.TestCase):

    def test_rules_structure(self):
        """验证规则库必须包含必要字段"""
        self.assertGreater(len(fast_scan.RULES), 20, "规则库规则数量不足")
        for r in fast_scan.RULES:
            self.assertIn("id", r)
            self.assertIn("pattern", r)
            self.assertIn("app", r)
            self.assertIn("level", r)
            self.assertIn("desc", r)
            self.assertIn("suggest", r)

    def test_kill_switch_forbidden_paths(self):
        """验证 Kill Switch 核心物理熔断机制"""
        forbidden_test_cases = [
            "/System/Library/CoreServices",
            "/usr/bin/python3",
            "/bin/bash",
            os.path.expanduser("~/Library/Keychains/login.keychain-db"),
            os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/Cookies"),
            os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/Login State"),
            os.path.expanduser("~/Library/Application Support/LarkShell/sdk_storage/accounts.sqlite"),
        ]
        for path in forbidden_test_cases:
            self.assertTrue(
                fast_scan.is_forbidden(path),
                f"安全熔断失效：未能拦截禁止路径 {path}"
            )
            with self.assertRaises(PermissionError):
                fast_scan.safe_clean_path(path, dry_run=True)

    def test_sensitive_file_deep_guard(self):
        """验证二级深度防御：潜藏敏感凭证/私钥文件时熔断拦截"""
        test_dir = os.path.expanduser("~/.cache/disk-raccoon/test_safe_guard")
        os.makedirs(test_dir, exist_ok=True)
        try:
            secret_file = os.path.join(test_dir, "id_rsa_backup.key")
            with open(secret_file, "w") as f:
                f.write("FAKE KEY")

            detected = fast_scan.check_sensitive_content(test_dir)
            self.assertIsNotNone(detected, "未能检测到敏感私钥文件")

            with self.assertRaises(fast_scan.SecurityAlertException):
                fast_scan.safe_clean_path(test_dir, dry_run=True)
        finally:
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)

    def test_symlink_no_traversal(self):
        """验证符号链接防御：只解绑链接自身，绝不穿透删除真实文件"""
        test_dir = os.path.expanduser("~/.cache/disk-raccoon/test_symlink_guard")
        os.makedirs(test_dir, exist_ok=True)
        try:
            real_target = os.path.join(test_dir, "real_important_file.txt")
            with open(real_target, "w") as f:
                f.write("KEEP ME SAFE")

            symlink_path = os.path.join(test_dir, "link_to_important")
            os.symlink(real_target, symlink_path)

            ok, msg = fast_scan.safe_clean_path(symlink_path, dry_run=False)
            self.assertTrue(ok)
            self.assertFalse(os.path.islink(symlink_path))
            self.assertTrue(os.path.exists(real_target))
        finally:
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)

    def test_target_selector_precision(self):
        """验证目标选择器的精准匹配：按应用名、序号、规则ID匹配，且防止 pnpm 误伤 npm"""
        item_npm = {"id": 5, "rule_id": "npm-cache", "app": "npm", "path": "/Users/test/.npm"}
        item_pnpm = {"id": 2, "rule_id": "pnpm-store-lib", "app": "pnpm", "path": "/Users/test/Library/pnpm/store"}
        item_gradle = {"id": 1, "rule_id": "gradle-cache", "app": "Gradle", "path": "/Users/test/.gradle/caches"}

        # 1. 匹配 pnpm 时，不能命中 npm
        self.assertTrue(fast_scan.is_item_selected(item_pnpm, ["pnpm"]))
        self.assertFalse(fast_scan.is_item_selected(item_npm, ["pnpm"]))

        # 2. 匹配 npm 时，不能命中 pnpm
        self.assertTrue(fast_scan.is_item_selected(item_npm, ["npm"]))
        self.assertFalse(fast_scan.is_item_selected(item_pnpm, ["npm"]))

        # 3. 按数字序号匹配
        self.assertTrue(fast_scan.is_item_selected(item_gradle, ["1"]))
        self.assertFalse(fast_scan.is_item_selected(item_gradle, ["2"]))

        # 4. 按规则ID匹配
        self.assertTrue(fast_scan.is_item_selected(item_gradle, ["gradle-cache"]))

    def test_cjk_width_alignment(self):
        """验证中文字符在终端中的宽度计算（CJK=2, 半角=1）"""
        self.assertEqual(fast_scan.string_width("abc"), 3)
        self.assertEqual(fast_scan.string_width("小浣熊"), 6)
        self.assertEqual(fast_scan.string_width("abc小浣熊"), 9)

        padded = fast_scan.pad_text("小浣熊", 10)
        self.assertEqual(fast_scan.string_width(padded), 10)

    def test_calc_savings(self):
        """验证苹果 SSD 升配费用等价换算（512GB = ¥1500）"""
        bytes_512g = 512 * 1024 * 1024 * 1024
        savings = fast_scan.calc_savings_cny(bytes_512g)
        self.assertEqual(savings, 1500.0)

    def test_concurrency_lock(self):
        """验证并发排他锁"""
        with fast_scan.ProcessLock():
            self.assertTrue(os.path.exists(fast_scan.LOCK_FILE))
        self.assertFalse(os.path.exists(fast_scan.LOCK_FILE))

if __name__ == "__main__":
    unittest.main()
