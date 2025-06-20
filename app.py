import os
import json
from flask import Flask, request, render_template, redirect

from datetime import datetime

app = Flask(__name__)

TOKENS_FILE = os.path.join(os.path.dirname(__file__), "tokens.json")

def carregar_tokens():
    with open(TOKENS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

@app.route("/completar-cadastro")
def completar_cadastro():
    token_recebido = request.args.get("token")

    tokens = carregar_tokens()
    usuario = next((t for t in tokens if t["token"] == token_recebido), None)

    if not usuario:
        return "❌ Token inválido ou não encontrado", 404

    if usuario.get("usado"):
        return "⚠️ Esse token já foi usado.", 403

    if datetime.fromisoformat(usuario["expira_em"]) < datetime.now():
        return "⚠️ Esse token expirou.", 403

    return render_template("completar_cadastro.html", usuario=usuario)



@app.route("/finalizar-cadastro", methods=["POST"])
def finalizar_cadastro():
    token_recebido = request.form.get("token")
    senha = request.form.get("senha")
    idade = request.form.get("idade")
    cargo = request.form.get("cargo")

    tokens = carregar_tokens()
    usuario = next((t for t in tokens if t["token"] == token_recebido), None)

    if not usuario:
        return "❌ Token inválido", 404

    # Atualiza dados
    usuario["senha"] = senha
    usuario["idade"] = idade
    usuario["cargo"] = cargo
    usuario["usado"] = True

    # Salva no arquivo
    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2, ensure_ascii=False)

    # Redireciona para o formulário correto
    base_metform = "https://gestor.thehrkey.tech/formularios/"
    url_final = f"{base_metform}{usuario['produto']}_{usuario['tipo']}.html"

    return redirect(url_final)

