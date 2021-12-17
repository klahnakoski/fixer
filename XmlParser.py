# encoding: utf-8
import ast

from mo_dots import unwraplist
from mo_parsing import (
    Whitespace,
    Literal,
    Regex,
    Word,
    Group,
    Forward,
    Log,
    ParseException,
    Optional,
    OneOrMore,
    Suppress,
    SkipTo,
    OpenDict,
)

tag_stack = []


def push_name(tokens):
    tag_stack.append(tokens[0])


def pop_name(tokens, index, string):
    expecting = tag_stack[-1]
    if tokens[0] == expecting:
        tag_stack.pop()
        return
    raise ParseException(tokens.type, index, string, f"expecting close tag {expecting}")


def pop():
    tag_stack.pop()


def unquote(tokens):
    return ast.literal_eval(tokens[0])


class XmlParser(object):
    def __init__(self):
        with Whitespace() as white:
            white.set_literal(lambda v: Literal(v).suppress())

            init = "".join(sorted(set(
                Regex("[A-Za-z:_\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF]")
                .expr
                .parser_config
                .include
            )))
            rest = "".join(sorted(
                set(Regex("[\\-.0-9\u00B7\u0300-\u036F]").expr.parser_config.include)
                | set(init)
            ))
            name = Word(init_chars=init, body_chars=rest)

            attr = Group(
                name / (lambda t: t[0])
                + "="
                + ((Regex('"[^"]*"') | Regex("'[^']*'")) / unquote)
            )

            text = Regex("[^<]+")
            tag = Forward()
            cdata = "<![CDATA[" + SkipTo("]]>") / (lambda t: t[0])

            tag << (
                "<"
                + (name("name") / push_name)
                + Optional((OpenDict(OneOrMore(attr)) / dict)("attributes"))
                + (
                    Suppress("/>") / pop
                    | (
                        ">"
                        + Optional(Group(OneOrMore(tag | cdata | text))("children"))
                        + "</"
                        + (name / pop_name)
                        + ">"
                    )
                )
            ) / dict

            self.tag = OneOrMore(tag | cdata | text).finalize()

    def parse(self, content):
        tag_stack.clear()
        try:
            return self.tag.parse(content)[0]
        finally:
            if tag_stack:
                Log.error(
                    "expecting closing tags: {{tags}}",
                    tags=unwraplist(list(reversed(tag_stack))),
                )


parse = XmlParser().parse
