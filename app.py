from flask import Flask, request, render_template, redirect
import json
import os
from datetime import datetime

app = Flask(__name__)

# Carregar dados dos tokens
TOKENS_FILE = os.path.join(os.path.dirname(__file__), "tokens.json")

if os.path.exists(TOKENS_FILE):
    with open(TOKENS_FILE, "r", encoding="utf-8") as f:
        tokens = json.load(f)
else:
    tokens = []

# Página de cadastro via token
@app.route("/completar-cadastro")
def completar_cadastro():
    token = request.args.get("token")
    if not token:
        return "Token não informado.", 400

    usuario = next((u for u in tokens if u["token"] == token), None)
    if not usuario:
        return "Token inválido.", 403

    expiracao = datetime.strptime(usuario["expira_em"], "%Y-%m-%dT%H:%M:%S")
    if datetime.now() > expiracao:
        return "Token expirado.", 403

    if usuario.get("usado"):
        return "Este link já foi utilizado.", 403

    return render_template("completar_cadastro.html", usuario=usuario)

@app.route("/finalizar-cadastro", methods=["POST"])
def finalizar_cadastro():
    token = request.form.get("token")
    for u in tokens:
        if u["token"] == token:
            u["usado"] = True
            break
    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2, ensure_ascii=False)
    return "Cadastro concluído com sucesso!"

if __name__ == "__main__":
    app.run(debug=True)
