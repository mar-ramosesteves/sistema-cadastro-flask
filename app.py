import os
import json
from flask import Flask, request, render_template, redirect
from datetime import datetime
from urllib.parse import urlencode

app = Flask(__name__)

TOKENS_FILE = os.path.join(os.path.dirname(__file__), "tokens.json")

def carregar_tokens():
    try:
        with open(TOKENS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list) and all(isinstance(item, dict) for item in data):
                return data
            else:
                print("❌ ERRO: tokens.json não está no formato esperado (lista de dicionários).")
                return []
    except Exception as e:
        print(f"❌ ERRO ao carregar tokens: {e}")
        return []

@app.route("/")
def home():
    return "✅ API do Sistema de Cadastro está no ar!"

@app.route("/completar-cadastro")
def completar_cadastro():
    token_recebido = request.args.get("token")
    tokens = carregar_tokens()

    usuario = next((t for t in tokens if t.get("token") == token_recebido), None)

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
    usuario = next((t for t in tokens if t.get("token") == token_recebido), None)

    if not usuario:
        return "❌ Token inválido", 404

    usuario["senha"] = senha
    usuario["idade"] = idade
    usuario["cargo"] = cargo
    usuario["usado"] = True

    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2, ensure_ascii=False)

    if usuario["produto"] == "arquetipos":
        if usuario["tipo"] == "autoavaliacao":
            url_base = "https://gestor.thehrkey.tech/form_arquetipos_autoaval"
        else:
            url_base = "https://gestor.thehrkey.tech/form_arquetipos"
    elif usuario["produto"] == "microambiente":
        url_base = "https://gestor.thehrkey.tech/microambiente-de-equipes"
    else:
        return "❌ Produto ou tipo inválido", 400

        # Parâmetros que serão enviados para o MetForm
    parametros = {
        "email": usuario["email"],
        "emailLider": usuario["emailLider"],
        "empresa": usuario["empresa"],
        "codrodada": usuario["codrodada"],
        "nome": usuario["nome"],
        "tipo": usuario["tipo"]
    }

    url_final = f"{url_base}?{urlencode(parametros, doseq=True)}"
    return redirect(url_final)


   
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
