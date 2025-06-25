import os
import json
import smtplib
import pandas as pd
import uuid
from flask import Flask, request, render_template, redirect
from datetime import datetime, timedelta
from urllib.parse import urlencode
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

TOKENS_FILE = os.path.join(os.path.dirname(__file__), "tokens.json")

# Função para carregar tokens existentes
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
        print(f"✅ TOKENS GERADOS: {json.dumps(tokens, indent=2, ensure_ascii=False)}")

    if usuario["produto"] == "arquetipos":
        if usuario["tipo"] == "autoavaliacao":
            url_base = "https://gestor.thehrkey.tech/form_arquetipos_autoaval"
        else:
            url_base = "https://gestor.thehrkey.tech/form_arquetipos"
    elif usuario["produto"] == "microambiente":
        url_base = "https://gestor.thehrkey.tech/microambiente-de-equipes"
    else:
        return "❌ Produto ou tipo inválido", 400

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

@app.route("/upload", methods=["GET", "POST"])
def upload_excel():
    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            return "❌ Nenhum arquivo enviado.", 400

        try:
            df = pd.read_excel(file)
            tokens = []
            for _, row in df.iterrows():
                token = {
                    "nome": row.get("nome", "").strip(),
                    "email": row.get("email", "").strip(),
                    "empresa": row.get("company", "").strip(),
                    "codrodada": row.get("codrodada", "").strip(),
                    "produto": row.get("produto", "").strip().lower(),
                    "tipo": row.get("tipo", "").strip().lower(),
                    "nomeLider": row.get("nomeLider", "").strip(),
                    "emailLider": row.get("emailLider", "").strip(),
                    "token": uuid.uuid4().hex,
                    "expira_em": (datetime.now() + timedelta(days=2)).isoformat(),
                    "usado": False
                }
                tokens.append(token)

            with open(TOKENS_FILE, "w", encoding="utf-8") as f:
                json.dump(tokens, f, indent=2, ensure_ascii=False)

            return f"✅ {len(tokens)} tokens gerados com sucesso e salvos no tokens.json."
        except Exception as e:
            return f"❌ Erro ao processar o Excel: {e}", 500

    return '''
    <!doctype html>
    <title>Upload Excel</title>
    <h2>Upload de Planilha Excel para Gerar Tokens</h2>
    <form method="post" enctype="multipart/form-data">
      <input type="file" name="file" accept=".xlsx">
      <input type="submit" value="Enviar">
    </form>
    '''

@app.route("/listar-tokens")
def listar_tokens():
    tokens = carregar_tokens()
    html = "<h2>✅ TOKENS GERADOS</h2><ul style='font-family:monospace;'>"
    for t in tokens:
        html += "<li>"
        html += "<br>".join([
            f"<b>Nome:</b> {t['nome']}",
            f"<b>Email:</b> {t['email']}",
            f"<b>Empresa:</b> {t['empresa']}",
            f"<b>Produto:</b> {t['produto']}",
            f"<b>Tipo:</b> {t['tipo']}",
            f"<b>Token:</b> <code>{t['token']}</code>",
            f"<b>Expira em:</b> {t['expira_em']}",
            f"<b>Usado:</b> {t['usado']}"
        ])
        html += "</li><hr>"
    html += "</ul>"
    return html

@app.route("/excluir-tokens", methods=["GET", "POST"])
def excluir_tokens():
    if request.method == "POST":
        try:
            with open(TOKENS_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2, ensure_ascii=False)
            return "✅ Todos os tokens foram excluídos com sucesso!"
        except Exception as e:
            return f"❌ Erro ao excluir os tokens: {e}"
    return '''
        <h2>Confirmação de Exclusão</h2>
        <p style="color:red;"><strong>ATENÇÃO:</strong> Esta ação vai apagar <u>todos</u> os tokens salvos. Isso é irreversível.</p>
        <form method="post">
            <button type="submit" style="padding:10px 20px; background:red; color:white; border:none; border-radius:8px;">Excluir TODOS os tokens</button>
        </form>
        <p><a href="/listar-tokens">Voltar</a></p>
    '''

@app.route("/enviar-emails")
def enviar_emails():
    tokens = carregar_tokens()
    enviados = 0

    smtp_host = "mail.thehrkey.tech"
    smtp_port = 465
    smtp_user = "futurorh@thehrkey.tech"
    smtp_pass = "1Tubar@o"

    for usuario in tokens:
        if usuario.get("usado"):
            continue

        if usuario["produto"] == "arquetipos":
            if usuario["tipo"] == "autoavaliacao":
                url = "https://gestor.thehrkey.tech/form_arquetipos_autoaval"
            else:
                url = "https://gestor.thehrkey.tech/form_arquetipos"
        elif usuario["produto"] == "microambiente":
            url = "https://gestor.thehrkey.tech/microambiente-de-equipes"
        else:
            continue

        parametros = {
            "email": usuario["email"],
            "emailLider": usuario["emailLider"],
            "empresa": usuario["empresa"],
            "codrodada": usuario["codrodada"],
            "nome": usuario["nome"],
            "tipo": usuario["tipo"]
        }

        link = f"{url}?{urlencode(parametros, doseq=True)}"

        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = usuario["email"]
        msg["Subject"] = "[THE HR KEY] Link de Avaliação - Acesso Pessoal"

        texto = f"""
Olá {usuario['nome']},

Seu link de avaliação está pronto. Clique no botão abaixo para acessar:

👉 {link}

Esse link é pessoal, intransferível e válido por até 2 dias. Só pode ser usado uma vez.

Atenciosamente,
The HR Key
"""
        msg.attach(MIMEText(texto, "plain"))

        try:
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
                enviados += 1
        except Exception as e:
            print(f"❌ Erro ao enviar para {usuario['email']}: {e}")

    return f"✅ E-mails enviados com sucesso: {enviados}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
