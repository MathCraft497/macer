from .tokens import Token, TokenType
from . import ast_nodes as ast
from .diagnostics import (
    DiagnosticBag, MacerCompileError, Diagnostic, Span, Severity, ErrCode
)


# 运算符符号 → 内部 key
OPERATOR_SYMBOLS = {
    "+": "opr+", "-": "opr-", "*": "opr*", "/": "opr/",
    "==": "opr==", "!=": "opr!=", "<": "opr<", ">": "opr>",
}


class Parser:
    def __init__(self, tokens, filename="<source>", bag=None,
                 source=""):
        self.tokens = tokens
        self.filename = filename
        self.pos = 0
        self.bag = bag if bag is not None else DiagnosticBag()
        self.source = source       # 原始源码，用于切片字符串

    # ---------- 辅助 ----------
    def peek(self, offset=0):
        p = self.pos + offset
        return self.tokens[p] if p < len(self.tokens) else self.tokens[-1]

    def check(self, *types):
        return self.peek().type in types

    def match(self, *types):
        if self.check(*types):
            t = self.peek()
            self.pos += 1
            return t
        return None

    def _err(self, code, msg, tok=None, width=None):
        tok = tok or self.peek()
        if tok.value is not None:
            w = len(str(tok.value))
        else:
            w = 1
        if width is not None:
            w = width
        diag = Diagnostic(
            code=code, severity=Severity.ERROR, message=msg,
            span=Span(tok.line, tok.col, tok.line, tok.col + max(w, 1)),
            filename=self.filename,
        )
        self.bag.add(diag)
        raise MacerCompileError(diag)

    def expect(self, ttype, msg=None):
        if not self.check(ttype):
            tok = self.peek()
            expected = ttype.name
            got = tok.type.name if tok.type != TokenType.EOF else "文件结尾"
            text = f"期望 {expected}，但遇到 {got}"
            if tok.value is not None:
                text += f" ({tok.value!r})"
            if msg:
                text += f" —— {msg}"
            self._err(ErrCode.PARSE_EXPECTED, text, tok)
        t = self.peek()
        self.pos += 1
        return t

    # ---------- 类型 ----------
    def parse_type(self):
        # 基础类型或类名
        if self.check(TokenType.TYPE_INT, TokenType.TYPE_FLOAT,
                      TokenType.TYPE_STRING, TokenType.TYPE_BOOL,
                      TokenType.TYPE_VOID, TokenType.TYPE_ANY,
                      TokenType.TYPE_CHAR):
            tok = self.peek();
            self.pos += 1
            node = ast.TypeNode(tok.value, [])
        elif self.check(TokenType.IDENT):
            name = self.peek().value;
            self.pos += 1
            generics = []
            if self.match(TokenType.LT):
                generics.append(self.parse_type())
                while self.match(TokenType.COMMA):
                    generics.append(self.parse_type())
                self.expect(TokenType.GT)
            node = ast.TypeNode(name, generics)
        else:
            self._err(ErrCode.PARSE_EXPECTED, "这里期待一个类型")

        # 数组后缀 []
        while self.check(TokenType.LBRACKET) and \
                self.peek(1).type == TokenType.RBRACKET:
            self.pos += 2
            node.is_array = True
            node.array_dims += 1

        return node

    # ---------- 程序 ----------
    def parse(self):
        prog = ast.Program()

        if self.check(TokenType.PACKAGE):
            prog.package = self.parse_package()

        while self.check(TokenType.IMPORT, TokenType.FROM):
            prog.imports.append(self.parse_import())

        while not self.check(TokenType.EOF):
            prog.declarations.append(self.parse_declaration())

        return prog

    def parse_package(self):
        tok = self.expect(TokenType.PACKAGE)
        line, col = tok.line, tok.col
        parts = [self.expect(TokenType.IDENT).value]
        while self.match(TokenType.DOT):
            parts.append(self.expect(TokenType.IDENT).value)
        self.match(TokenType.SEMICOLON)
        return ast.PackageDecl(".".join(parts), line, col)

    def parse_import(self):
        tok = self.peek()
        line, col = tok.line, tok.col

        if self.check(TokenType.IMPORT):
            self.pos += 1
            parts = [self.expect(TokenType.IDENT).value]
            while self.match(TokenType.DOT):
                if self.match(TokenType.STAR):
                    self.match(TokenType.SEMICOLON)
                    return ast.ImportDecl(module=".".join(parts),
                                          is_wildcard=True,
                                          line=line, col=col)
                parts.append(self.expect(TokenType.IDENT).value)
            alias = None
            if self.match(TokenType.AS):
                alias = self.expect(TokenType.IDENT).value
            self.match(TokenType.SEMICOLON)
            return ast.ImportDecl(module=".".join(parts), alias=alias,
                                  line=line, col=col)
        else:
            self.expect(TokenType.FROM)
            parts = [self.expect(TokenType.IDENT).value]
            while self.match(TokenType.DOT):
                parts.append(self.expect(TokenType.IDENT).value)
            self.expect(TokenType.IMPORT)
            names = [self.expect(TokenType.IDENT).value]
            while self.match(TokenType.COMMA):
                names.append(self.expect(TokenType.IDENT).value)
            self.match(TokenType.SEMICOLON)
            return ast.ImportDecl(module=".".join(parts), names=names,
                                  line=line, col=col)

    def parse_declaration(self):
        is_public = True
        if self.match(TokenType.PUBLIC):
            is_public = True
        elif self.match(TokenType.PRIVATE):
            is_public = False

        if self.check(TokenType.CLASS):
            return self.parse_class(is_public)
        if self.check(TokenType.FUNC):
            return self.parse_func(is_public=is_public, is_method=False)
        self._err(ErrCode.PARSE_UNEXPECTED,
                  "这里期待 class / func 声明")

    def parse_class(self, is_public=True):
        tok = self.expect(TokenType.CLASS)
        line, col = tok.line, tok.col
        name = self.expect(TokenType.IDENT).value
        parent = None
        if self.match(TokenType.EXTENDS):
            parent = self.expect(TokenType.IDENT).value
        self.expect(TokenType.LBRACE, "类体开始")

        fields, methods = [], []
        while not self.check(TokenType.RBRACE, TokenType.EOF):
            while not self.check(TokenType.RBRACE, TokenType.EOF):
                member_public = True
                if self.match(TokenType.PUBLIC):
                    member_public = True
                elif self.match(TokenType.PRIVATE):
                    member_public = False

                # @overload 装饰
                overload = False
                if self.check(TokenType.AT):
                    self.pos += 1
                    # 期望 @overload
                    if self.check(TokenType.IDENT) and self.peek().value == "overload":
                        self.pos += 1
                        overload = True
                    else:
                        self._err(ErrCode.PARSE_UNEXPECTED,
                                  "期望 @overload 装饰器")

                if self.check(TokenType.FUNC):
                    methods.append(self.parse_func(member_public, is_method=True,
                                                   overload=overload))
                elif self.check(TokenType.IDENT):
                    fields.append(self.parse_field(member_public))
                else:
                    self._err(ErrCode.PARSE_UNEXPECTED,
                              "类体中期待字段或方法声明")

        self.expect(TokenType.RBRACE, "类体结束")
        return ast.ClassDecl(name, parent, fields, methods, is_public,
                             line, col)

    def parse_field(self, is_public):
        name_tok = self.expect(TokenType.IDENT)
        line, col = name_tok.line, name_tok.col
        name = name_tok.value
        self.expect(TokenType.COLON, "字段类型标注")
        type_node = self.parse_type()
        init = None
        if self.match(TokenType.EQ):
            init = self.parse_expression()
        self.match(TokenType.SEMICOLON)
        return ast.FieldDecl(name, type_node, init, is_public, line, col)

    # ---------- 运算符函数名解析 ----------
    def _try_parse_calc_func_name(self):
        """
        calc.get.opr  /  calc.set.opr  /  calc.opr+  /  calc.opr== ...
        返回 (display_name, op_key) 或 None
        """
        if not self.check(TokenType.CALC):
            return None
        saved = self.pos
        self.pos += 1

        # calc.get.opr  /  calc.set.opr  /  calc.get.opr[]
        # token:  CALC  DOT  IDENT(get/set)  DOT  IDENT(opr)
        if (self.check(TokenType.DOT) and
                self.peek(1).type == TokenType.IDENT and
                self.peek(1).value in ("get", "set") and
                self.peek(2).type == TokenType.DOT and
                self.peek(3).type == TokenType.IDENT and
                self.peek(3).value == "opr"):
            first = self.peek(1).value  # "get" / "set"
            self.pos += 4  # 跳过 . get/set . opr
            # 可选 []
            if self.check(TokenType.LBRACKET):
                self.pos += 1
                self.expect(TokenType.RBRACKET, "opr[] 缺少 ]")
            return (f"calc.{first}.opr", f"{first}.opr")

        # calc.opr<符号> / calc.opr()
        # token:  CALC  DOT  IDENT("opr")  <符号或 ( >
        if (self.check(TokenType.DOT)
                and self.peek(1).type == TokenType.IDENT
                and self.peek(1).value == "opr"):
            self.pos += 2  # ← 跳过 . opr
            if self.check(TokenType.PLUS, TokenType.MINUS, TokenType.STAR,
                          TokenType.SLASH, TokenType.EQEQ, TokenType.NEQ,
                          TokenType.LT, TokenType.GT):
                op_tok = self.peek();
                self.pos += 1
                key = OPERATOR_SYMBOLS.get(op_tok.value)
                if key:
                    return (f"calc.{key}", key)
            if self.check(TokenType.LPAREN):
                self.pos += 1
                self.expect(TokenType.RPAREN, "opr() 缺少 )")
                return ("calc.opr()", "opr()")

        self.pos = saved
        return None

    def parse_func(self, is_public=True, is_method=False, overload=False):
        tok = self.expect(TokenType.FUNC)
        line, col = tok.line, tok.col

        op_result = self._try_parse_calc_func_name()
        if op_result is not None:
            name, op_key = op_result
        else:
            name = self.expect(TokenType.IDENT).value
            op_key = None

        self.expect(TokenType.LPAREN, "函数参数列表开始")
        params = []
        if not self.check(TokenType.RPAREN):
            params.append(self.parse_param())
            while self.match(TokenType.COMMA):
                params.append(self.parse_param())
        self.expect(TokenType.RPAREN, "函数参数列表结束")

        return_type = ast.TypeNode("Void", [])
        if self.match(TokenType.ARROW):
            return_type = self.parse_type()

        if self.match(TokenType.SEMICOLON):
            body = []
        else:
            body = self.parse_block()

        return ast.FuncDecl(name, params, return_type, body,
                            is_method, is_public, line, col, op_key,
                            overload)

    def parse_param(self):
        name = self.expect(TokenType.IDENT).value
        self.expect(TokenType.COLON, "参数类型标注")
        t = self.parse_type()
        return ast.Param(name, t)

    def parse_block(self):
        self.expect(TokenType.LBRACE, "语句块开始")
        stmts = []
        while not self.check(TokenType.RBRACE, TokenType.EOF):
            stmts.append(self.parse_statement())
        self.expect(TokenType.RBRACE, "语句块结束")
        return stmts

    # ---------- 语句 ----------
    def parse_statement(self):
        tok = self.peek()
        if tok.type in (TokenType.VAR, TokenType.LET):
            return self.parse_var_decl()
        if tok.type == TokenType.IF:
            return self.parse_if()
        if tok.type == TokenType.WHILE:
            return self.parse_while()
        if tok.type == TokenType.RETURN:
            return self.parse_return()
        if tok.type == TokenType.LBRACE:
            line, col = tok.line, tok.col
            return ast.Block(self.parse_block(), line, col)

        expr = self.parse_expression()
        self.match(TokenType.SEMICOLON)
        return ast.ExprStmt(expr, tok.line, tok.col)

    def parse_var_decl(self):
        tok = self.peek()
        mutable = tok.type == TokenType.VAR
        self.pos += 1
        name = self.expect(TokenType.IDENT).value
        self.expect(TokenType.COLON, "变量声明需要类型标注")
        type_node = self.parse_type()
        init = None
        if self.match(TokenType.EQ):
            init = self.parse_expression()
        self.match(TokenType.SEMICOLON)
        return ast.VarDecl(name, type_node, init, mutable, tok.line, tok.col)

    def parse_if(self):
        tok = self.expect(TokenType.IF)
        line, col = tok.line, tok.col
        cond = self.parse_expression()
        then_body = self.parse_block()
        else_body = None
        if self.match(TokenType.ELSE):
            if self.check(TokenType.IF):
                else_body = [self.parse_if()]
            else:
                else_body = self.parse_block()
        return ast.IfStmt(cond, then_body, else_body, line, col)

    def parse_while(self):
        tok = self.expect(TokenType.WHILE)
        line, col = tok.line, tok.col
        cond = self.parse_expression()
        body = self.parse_block()
        return ast.WhileStmt(cond, body, line, col)

    def parse_return(self):
        tok = self.expect(TokenType.RETURN)
        line, col = tok.line, tok.col
        value = None
        if not self.check(TokenType.SEMICOLON, TokenType.RBRACE):
            value = self.parse_expression()
        self.match(TokenType.SEMICOLON)
        return ast.ReturnStmt(value, line, col)

    # ---------- 表达式 ----------
    def parse_expression(self):
        return self.parse_assignment()

    def parse_assignment(self):
        left = self.parse_or()
        if self.match(TokenType.EQ):
            value = self.parse_assignment()
            if isinstance(left, ast.Ident):
                return ast.Assign(left, value, left.line, left.col)
            if isinstance(left, ast.FieldAccess):
                return ast.Assign(left, value, left.line, left.col)
            if isinstance(left, ast.IndexExpr):
                return ast.IndexAssign(left.obj, left.index, value,
                                       left.line, left.col)
            self._err(ErrCode.PARSE_BAD_ASSIGN,
                      "赋值语句左侧必须是变量、字段或索引",
                      self.peek(-1) if self.pos > 0 else None)
        return left

    def parse_or(self):
        left = self.parse_and()
        while self.check(TokenType.OR):
            op_tok = self.peek(); self.pos += 1
            right = self.parse_and()
            left = ast.Binary("||", left, right, op_tok.line, op_tok.col)
        return left

    def parse_and(self):
        left = self.parse_equality()
        while self.check(TokenType.AND):
            op_tok = self.peek(); self.pos += 1
            right = self.parse_equality()
            left = ast.Binary("&&", left, right, op_tok.line, op_tok.col)
        return left

    def parse_equality(self):
        left = self.parse_comparison()
        while self.check(TokenType.EQEQ, TokenType.NEQ):
            op_tok = self.peek(); self.pos += 1
            right = self.parse_comparison()
            left = ast.Binary(op_tok.value, left, right, op_tok.line, op_tok.col)
        return left

    def parse_comparison(self):
        left = self.parse_term()
        while self.check(TokenType.LT, TokenType.GT, TokenType.LE, TokenType.GE):
            op_tok = self.peek(); self.pos += 1
            right = self.parse_term()
            left = ast.Binary(op_tok.value, left, right, op_tok.line, op_tok.col)
        return left

    def parse_term(self):
        left = self.parse_factor()
        while self.check(TokenType.PLUS, TokenType.MINUS):
            op_tok = self.peek(); self.pos += 1
            right = self.parse_factor()
            left = ast.Binary(op_tok.value, left, right, op_tok.line, op_tok.col)
        return left

    def parse_factor(self):
        left = self.parse_unary()
        while self.check(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op_tok = self.peek(); self.pos += 1
            right = self.parse_unary()
            left = ast.Binary(op_tok.value, left, right, op_tok.line, op_tok.col)
        return left

    def parse_unary(self):
        if self.check(TokenType.MINUS, TokenType.NOT):
            op_tok = self.peek(); self.pos += 1
            operand = self.parse_unary()
            return ast.Unary(op_tok.value, operand, op_tok.line, op_tok.col)
        return self.parse_postfix()

    # ---------- 方括号切片：读取原始文本 ----------
    def parse_bracket_dual(self):
        """解析 [xxx]，同时得到 raw 字符串和 expr 表达式"""
        lb = self.expect(TokenType.LBRACKET)
        line, col = lb.line, lb.col
        start_pos = lb.end_pos
        start_tok_pos = self.pos

        # ① 扫描到匹配 ]
        depth = 1
        end_tok = None
        while self.pos < len(self.tokens):
            t = self.tokens[self.pos]
            if t.type == TokenType.LBRACKET:
                depth += 1
            elif t.type == TokenType.RBRACKET:
                depth -= 1
                if depth == 0:
                    end_tok = t
                    break
            self.pos += 1

        if end_tok is None:
            self._err(ErrCode.PARSE_UNEXPECTED, "缺少匹配的 ]", lb)

        # ② 提取原始文本
        if self.source:
            raw = self.source[start_pos:end_tok.start_pos].strip()
        else:
            raw = ""

        # ③ 回到开头，解析表达式
        saved_pos = self.pos
        self.pos = start_tok_pos
        try:
            expr = self.parse_expression()
        except MacerCompileError:
            # 解析表达式失败——可能里面是特殊语法
            # 用 SliceStringExpr 占位
            expr = ast.SliceStringExpr(raw, line, col)

        # ④ 跳到 ] 后面
        self.pos = saved_pos + 1

        return raw, expr, line, col

    def parse_postfix(self):
        expr = self.parse_primary()
        while True:
            if self.check(TokenType.DOT):
                dot_tok = self.peek(); self.pos += 1
                name_tok = self.expect(TokenType.IDENT)
                name = name_tok.value
                if self.check(TokenType.LPAREN):
                    args = self.parse_args()
                    callee = ast.FieldAccess(expr, name, dot_tok.line, dot_tok.col)
                    expr = ast.Call(callee, args, dot_tok.line, dot_tok.col)
                else:
                    expr = ast.FieldAccess(expr, name, dot_tok.line, dot_tok.col)
            elif self.check(TokenType.LBRACKET):
                raw, idx_expr, ln, cl = self.parse_bracket_dual()
                expr = ast.IndexExpr(expr, idx_expr, raw, ln, cl)
            elif self.check(TokenType.LPAREN):
                lp = self.peek()
                args = self.parse_args()
                expr = ast.Call(expr, args, lp.line, lp.col)
            else:
                break
        return expr

    def parse_args(self):
        self.expect(TokenType.LPAREN, "参数列表开始")
        args = []
        if not self.check(TokenType.RPAREN):
            args.append(self.parse_expression())
            while self.match(TokenType.COMMA):
                args.append(self.parse_expression())
        self.expect(TokenType.RPAREN, "参数列表结束")
        return args

    def parse_primary(self):
        tok = self.peek()
        line, col = tok.line, tok.col
        if self.match(TokenType.INT):
            return ast.IntLit(tok.value, line, col)
        if self.match(TokenType.FLOAT):
            return ast.FloatLit(tok.value, line, col)
        if self.match(TokenType.STRING):
            return ast.StringLit(tok.value, line, col)
        if self.match(TokenType.TRUE):
            return ast.BoolLit(True, line, col)
        if self.match(TokenType.FALSE):
            return ast.BoolLit(False, line, col)
        if self.match(TokenType.NULL):
            return ast.NullLit(line, col)
        if self.match(TokenType.SELF):
            return ast.SelfExpr(line, col)
        if self.match(TokenType.NEW):
            class_name = self.expect(TokenType.IDENT).value
            args = self.parse_args()
            return ast.NewExpr(class_name, args, line, col)
        if self.match(TokenType.LPAREN):
            e = self.parse_expression()
            self.expect(TokenType.RPAREN, "括号表达式结束")
            return e
        if self.check(TokenType.IDENT):
            name = self.expect(TokenType.IDENT).value
            return ast.Ident(name, line, col)

        if self.check(TokenType.LBRACKET):
            # 数组字面量
            lb = self.peek(); self.pos += 1
            elements = []
            if not self.check(TokenType.RBRACKET):
                elements.append(self.parse_expression())
                while self.match(TokenType.COMMA):
                    elements.append(self.parse_expression())
            self.expect(TokenType.RBRACKET, "数组字面量结束")
            return ast.ArrayLit(elements, lb.line, lb.col)

        self._err(ErrCode.PARSE_UNEXPECTED,
                  f"这里期待一个表达式，但遇到了 {tok.type.name}",
                  tok)