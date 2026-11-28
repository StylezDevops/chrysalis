"""The rules in force: universal rules and the K table from METHOD.md, grades from PROPORTION.md, and the condition language."""

from __future__ import annotations

import re

import proportion

from common import METHOD, PROPORTION, lookup, sabotaged, split_row


def parse_method(text: str):
    """Universal rules from '### Un. Title' headings, conditional rules from the K table."""
    universal = re.findall(r"(?m)^### (U\d+)\. (.+)$", text)
    conditional = []
    for line in text.splitlines():
        m = re.match(r"^\|\s*(K\d+)\s*\|\s*(.+?)\s*\|", line)
        if m:
            conditional.append((m.group(1), m.group(2).replace("`", "").strip()))
    return universal, conditional


def grades(text=None) -> dict:
    """The grade table of PROPORTION.md (one source; proportion.py parses it)."""
    return proportion.parse_grades(text or PROPORTION.read_text(encoding="utf-8-sig"), split_row)


TOKEN = re.compile(r'\s*(?:(\()|(\))|("[^"]*")|(==)|\b(and|or|not|in)\b|([A-Za-z_][\w.]*))')


class Condition:
    """A tiny parser for the K-table conditions: paths, "strings", ==, in, and, or, not, brackets."""

    def __init__(self, text: str):
        self.text = text
        self.tokens = self.tokenise(text)
        self.pos = 0
        self.tree = self.expr()
        if self.pos != len(self.tokens):
            raise ValueError(f"trailing tokens in condition: {text}")

    @staticmethod
    def tokenise(text):
        out, pos = [], 0
        text = text.strip()
        while pos < len(text):
            m = TOKEN.match(text, pos)
            if not m or m.end() == pos:
                raise ValueError(f"cannot parse condition at '{text[pos:]}': {text}")
            kinds = ["(", ")", "str", "==", "kw", "path"]
            for kind, val in zip(kinds, m.groups()):
                if val is not None:
                    out.append((kind if kind != "kw" else val, val))
            pos = m.end()
        return out

    def peek(self):
        return self.tokens[self.pos][0] if self.pos < len(self.tokens) else None

    def take(self, kind):
        if self.peek() != kind:
            raise ValueError(f"expected {kind} in condition: {self.text}")
        self.pos += 1
        return self.tokens[self.pos - 1][1]

    def expr(self):
        node = self.conj()
        while self.peek() == "or":
            self.pos += 1
            node = ("or", node, self.conj())
        return node

    def conj(self):
        node = self.neg()
        while self.peek() == "and":
            self.pos += 1
            node = ("and", node, self.neg())
        return node

    def neg(self):
        if self.peek() == "not":
            self.pos += 1
            return ("not", self.neg())
        return self.atom()

    def atom(self):
        if self.peek() == "(":
            self.pos += 1
            node = self.expr()
            self.take(")")
            return node
        if self.peek() == "str":
            s = self.take("str")[1:-1]
            self.take("in")
            return ("in", s, self.take("path"))
        path = self.take("path")
        if self.peek() == "==":
            self.pos += 1
            return ("eq", path, self.take("str")[1:-1])
        return ("truthy", path)

    def evaluate(self, cfg, node=None):
        node = node or self.tree
        op = node[0]
        if op == "or":
            return self.evaluate(cfg, node[1]) or self.evaluate(cfg, node[2])
        if op == "and":
            return self.evaluate(cfg, node[1]) and self.evaluate(cfg, node[2])
        if op == "not":
            return not self.evaluate(cfg, node[1])
        value = lookup(cfg, node[1] if op != "in" else node[2])
        value = None if value is KeyError else value
        if op == "eq":
            return value == node[2]
        if op == "in":
            return node[1] in (value or [])
        if value is None or isinstance(value, bool):
            return bool(value)
        # A bare path is a flag. "false" or 0 here would read as true, so anything but a bool is refused (U17).
        raise ValueError(f"{node[1]} must be true or false, got {value!r}")


def select_rules(cfg, method_text=None):
    universal, conditional = parse_method(method_text or METHOD.read_text(encoding="utf-8"))
    chosen = [(rid, title) for rid, title in universal]
    for rid, cond in conditional:
        if sabotaged("rules-ignore-conditions") or Condition(cond).evaluate(cfg):
            chosen.append((rid, cond))
    return chosen
