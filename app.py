import os
import json
import unicodedata
import uuid
import smtplib
from datetime import datetime, timedelta
from urllib.parse import urlencode, quote

import pandas as pd
from flask import Flask, request, render_template, redirect, session
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = 'sistema-cadastro-secret-key-2024'

TOKENS_FILE = os.path.join(os.path.dirname(__file__), "tokens.json")
LEADER_TRACK_TOKENS_FILE = os.path.join(os.path.dirname(__file__), "leader_track_tokens.json")


def normalizar(texto):
    return unicodedata.normalize('NFKD', str(texto)).encode('ASCII', 'ignore').decode('ASCII').strip().lower()


def carregar_tokens():
    if not os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2, ensure_ascii=False)

    try:
        with open(TOKENS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list) and all(isinstance(item, dict) for item in data):
                return data
            else:
                print("❌ ERRO: tokens.json não está no formato esperado.")
                return []
    except Exception as e:
        print(f"❌ ERRO ao carregar tokens: {e}")
        return []


def salvar_tokens(tokens):
    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2, ensure_ascii=False)


def carregar_leader_track_tokens():
    if not os.path.exists(LEADER_TRACK_TOKENS_FILE):
        print(f"📁 Criando arquivo: {LEADER_TRACK_TOKENS_FILE}")
        with open(LEADER_TRACK_TOKENS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2, ensure_ascii=False)

    try:
        with open(LEADER_TRACK_TOKENS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"📥 Carregando tokens: {len(data)} tokens encontrados")
            if isinstance(data, list) and all(isinstance(item, dict) for item in data):
                return data
            else:
                print("❌ ERRO: leader_track_tokens.json não está no formato esperado.")
                return []
    except Exception as e:
        print(f"❌ ERRO ao carregar leader track tokens: {e}")
        return []


def salvar_leader_track_tokens(tokens):
    with open(LEADER_TRACK_TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2, ensure_ascii=False)


def obter_config_email():
    remetente = "marceloesteves@thehrkey.tech"
    senha_remetente = "1Tub@r@o110368"
    smtp_server = "smtp.titan.email"
    porta = 465
    return remetente, senha_remetente, smtp_server, porta


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

    salvar_tokens(tokens)

    produto = normalizar(usuario.get("produto", ""))
    tipo = normalizar(usuario.get("tipo", ""))

    if produto == "arquetipos":
        if tipo == "autoavaliacao":
            url_base = "https://gestor.thehrkey.tech/form_arquetipos_autoaval"
        elif tipo == "avaliacao equipe":
            url_base = "https://gestor.thehrkey.tech/form_arquetipos"
        else:
            return f"⚠️ Tipo inválido para arquétipos: {tipo}", 400

    elif produto == "microambiente":
        if tipo in ["microambiente_equipe", "microambiente_autoavaliacao"]:
            url_base = "https://gestor.thehrkey.tech/microambiente-de-equipes"
        else:
            return f"⚠️ Tipo inválido para microambiente: {tipo}", 400

    else:
        return f"⚠️ Produto inválido: {produto}", 400

    parametros = {
        "email": usuario.get("email", ""),
        "emailLider": usuario.get("emailLider", ""),
        "empresa": usuario.get("empresa", ""),
        "codrodada": usuario.get("codrodada", ""),
        "nome": usuario.get("nome", ""),
        "tipo": usuario.get("tipo", "")
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
                    "nome": str(row.get("nome", "")).strip(),
                    "email": str(row.get("email", "")).strip(),
                    "empresa": str(row.get("company", "")).strip(),
                    "codrodada": str(row.get("codrodada", "")).strip(),
                    "produto": str(row.get("produto", "")).strip(),
                    "tipo": str(row.get("tipo", "")).strip(),
                    "nomeLider": str(row.get("nomeLider", "")).strip(),
                    "emailLider": str(row.get("emailLider", "")).strip(),
                    "token": uuid.uuid4().hex,
                    "expira_em": (datetime.now() + timedelta(days=2)).isoformat(),
                    "usado": False
                }
                tokens.append(token)

            salvar_tokens(tokens)
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
            f"<b>Nome:</b> {t.get('nome', '')}",
            f"<b>Email:</b> {t.get('email', '')}",
            f"<b>Empresa:</b> {t.get('empresa', '')}",
            f"<b>Produto:</b> {t.get('produto', '')}",
            f"<b>Tipo:</b> {t.get('tipo', '')}",
            f"<b>Token:</b> <code>{t.get('token', '')}</code>",
            f"<b>Expira em:</b> {t.get('expira_em', '')}",
            f"<b>Usado:</b> {t.get('usado', False)}"
        ])
        html += "</li><hr>"

    html += "</ul>"
    return html


@app.route("/excluir-tokens", methods=["GET", "POST"])
def excluir_tokens():
    if request.method == "POST":
        try:
            salvar_tokens([])
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


@app.route("/enviar-emails", methods=["GET"])
def enviar_emails():
    tokens = carregar_tokens()

    remetente, senha_remetente, smtp_server, porta = obter_config_email()

    enviados = 0
    pulados = 0
    erros = 0

    print(f"📦 Total de tokens carregados: {len(tokens)}")
    print(f"📨 Remetente configurado: {remetente}")
    print(f"🌐 SMTP: {smtp_server}:{porta}")

    for i, usuario in enumerate(tokens, start=1):
        try:
            nome = str(usuario.get("nome", "")).strip()
            email = str(usuario.get("email", "")).strip()
            produto = normalizar(usuario.get("produto", ""))
            tipo = normalizar(usuario.get("tipo", ""))
            token = str(usuario.get("token", "")).strip()

            print(f"\n--- Registro {i} ---")
            print(f"nome={nome}")
            print(f"email={email}")
            print(f"produto={produto}")
            print(f"tipo={tipo}")
            print(f"token={token[:8] if token else 'vazio'}...")

            if not nome or not email or not token:
                print("⏭️ Pulado: faltando nome, email ou token")
                pulados += 1
                continue

            if produto == "arquetipos":
                if tipo in ["autoavaliacao", "autoavaliacao "]:
                    url_base = "https://gestor.thehrkey.tech/form_arquetipos_autoaval"
                elif tipo in ["avaliacao equipe", "avaliacao de equipe"]:
                    url_base = "https://gestor.thehrkey.tech/form_arquetipos"
                else:
                    print(f"⏭️ Pulado: tipo inválido para arquétipos -> {tipo}")
                    pulados += 1
                    continue

            elif produto == "microambiente":
                if tipo in [
                    "microambiente_autoavaliacao",
                    "microambiente autoavaliacao"
                ]:
                    url_base = "https://gestor.thehrkey.tech/microambiente-de-equipes"
                elif tipo in [
                    "microambiente_equipe",
                    "microambiente equipe"
                ]:
                    url_base = "https://gestor.thehrkey.tech/microambiente-de-equipes"
                else:
                    print(f"⏭️ Pulado: tipo inválido para microambiente -> {tipo}")
                    pulados += 1
                    continue
            else:
                print(f"⏭️ Pulado: produto inválido -> {produto}")
                pulados += 1
                continue

            parametros = {
                "company": usuario.get("empresa", ""),
                "email": usuario.get("email", ""),
                "codrodada": usuario.get("codrodada", ""),
                "tipo": usuario.get("tipo", ""),
                "nome": usuario.get("nome", ""),
                "nomeLider": usuario.get("nomeLider", ""),
                "emailLider": usuario.get("emailLider", "")
            }

            query = "&".join(f"{k}={quote(str(v))}" for k, v in parametros.items())
            url_final = f"{url_base}?{query}"

            assunto = "🚀 Link de Acesso ao Formulário - The HR Key"
            corpo = f"""
            <p>Olá, <strong>{nome}</strong>!</p>
            <p>Segue o link de acesso ao formulário <strong>{produto.upper()} - {tipo.upper()}</strong>:</p>
            <p><a href="{url_final}" target="_blank">{url_final}</a></p>
            <p>⚠️ Este link é único, válido por 2 dias, e pode ser acessado apenas 1 vez.</p>
            <hr>
            <p style="font-size:12px;color:#777;">The HR Key | Programa de Liderança de Alta Performance</p>
            """

            msg = MIMEMultipart()
            msg["From"] = f"The HR Key <{remetente}>"
            msg["To"] = email
            msg["Subject"] = assunto
            msg.attach(MIMEText(corpo, "html"))

            with smtplib.SMTP_SSL(smtp_server, porta) as server:
                server.login(remetente, senha_remetente)
                server.sendmail(remetente, email, msg.as_string())

            enviados += 1
            print(f"✅ Enviado com sucesso para {email}")

        except Exception as e:
            erros += 1
            print(f"❌ Erro ao enviar para {usuario.get('email', 'sem email')}: {e}")

    return f"✅ Enviados: {enviados} | ⏭️ Pulados: {pulados} | ❌ Erros: {erros} | 📦 Total: {len(tokens)}"


@app.route("/validar-token-leadertrack")
def validar_token_leadertrack():
    try:
        token_recebido = request.args.get("token")
        tokens = carregar_leader_track_tokens()
        usuario = next((t for t in tokens if t.get("token") == token_recebido), None)

        if not usuario:
            return "❌ Token inválido ou não encontrado", 404

        email_lider = usuario.get("emailLider", "")
        empresa = usuario.get("empresa", "")
        codrodada = usuario.get("codrodada", "")

        url_leader_track = (
            f"https://gestor.thehrkey.tech/sistema-de-analise/"
            f"?company={quote(str(empresa))}"
            f"&codrodada={quote(str(codrodada))}"
            f"&emaillider={quote(str(email_lider))}"
            f"&token_validado=true"
        )

        return redirect(url_leader_track)

    except Exception as e:
        print(f"Erro na validação: {e}")
        return f"❌ Erro interno: {e}", 500


@app.route("/upload-leadertrack", methods=["GET", "POST"])
def upload_excel_leadertrack():
    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            return "❌ Nenhum arquivo enviado.", 400

        try:
            df = pd.read_excel(file)
            tokens = carregar_leader_track_tokens()

            for _, row in df.iterrows():
                email_lider = str(row.get("emailLider", "")).strip()
                token_existente = next((t for t in tokens if t.get("emailLider") == email_lider), None)

                if token_existente:
                    print(f"⚠️ Token já existe para {email_lider}, pulando...")
                    continue

                email_envio = str(row.get("emailEnvio", "")).strip()
                if not email_envio:
                    email_envio = email_lider

                token = {
                    "nomeLider": str(row.get("nomeLider", "")).strip(),
                    "emailLider": email_lider,
                    "emailEnvio": email_envio,
                    "empresa": str(row.get("company", "")).strip(),
                    "codrodada": str(row.get("codrodada", "")).strip(),
                    "token": uuid.uuid4().hex,
                    "criado_em": datetime.now().isoformat(),
                    "ativo": True
                }
                tokens.append(token)

            salvar_leader_track_tokens(tokens)
            return f"✅ {len(tokens)} tokens LeaderTrack gerados com sucesso!"

        except Exception as e:
            return f"❌ Erro ao processar o Excel: {e}", 500

    return '''
    <!doctype html>
    <title>Upload Excel - LeaderTrack</title>
    <h2>📊 Upload de Planilha Excel para Gerar Tokens LeaderTrack</h2>
    <p><strong>Formato esperado:</strong> nomeLider, emailLider, emailEnvio (opcional), company, codrodada</p>
    <p><em>Se não informar emailEnvio, será usado o emailLider como padrão</em></p>
    <form method="post" enctype="multipart/form-data">
      <input type="file" name="file" accept=".xlsx" required>
      <input type="submit" value="Gerar Tokens LeaderTrack">
    </form>
    '''


@app.route("/listar-tokens-leadertrack")
def listar_tokens_leadertrack():
    tokens = carregar_leader_track_tokens()
    html = "<h2>✅ TOKENS LEADERTRACK GERADOS</h2><ul style='font-family:monospace;'>"

    for t in tokens:
        html += "<li>"
        html += "<br>".join([
            f"<b>Nome do Líder:</b> {t.get('nomeLider', '')}",
            f"<b>Email do Líder:</b> {t.get('emailLider', '')}",
            f"<b>Email de Envio:</b> {t.get('emailEnvio', t.get('emailLider', ''))}",
            f"<b>Empresa:</b> {t.get('empresa', '')}",
            f"<b>Rodada:</b> {t.get('codrodada', '')}",
            f"<b>Token:</b> <code>{t.get('token', '')}</code>",
            f"<b>Criado em:</b> {t.get('criado_em', '')}",
            f"<b>Ativo:</b> {t.get('ativo', False)}"
        ])
        html += "</li><hr>"

    html += "</ul>"
    return html


@app.route("/excluir-tokens-leadertrack", methods=["GET", "POST"])
def excluir_tokens_leadertrack():
    if request.method == "POST":
        try:
            salvar_leader_track_tokens([])
            return "✅ Todos os tokens LeaderTrack foram excluídos com sucesso!"
        except Exception as e:
            return f"❌ Erro ao excluir os tokens: {e}"

    return '''
        <h2>Confirmação de Exclusão - LeaderTrack</h2>
        <p style="color:red;"><strong>ATENÇÃO:</strong> Esta ação vai apagar <u>todos</u> os tokens LeaderTrack salvos. Isso é irreversível.</p>
        <form method="post">
            <button type="submit" style="padding:10px 20px; background:red; color:white; border:none; border-radius:8px;">Excluir TODOS os tokens LeaderTrack</button>
        </form>
        <p><a href="/listar-tokens-leadertrack">Voltar</a></p>
    '''


@app.route("/enviar-emails-leadertrack", methods=["GET"])
def enviar_emails_leadertrack():
    tokens = carregar_leader_track_tokens()
    enviados = 0
    erros = 0

    remetente, senha_remetente, smtp_server, porta = obter_config_email()

    for usuario in tokens:
        try:
            nome_lider = usuario.get("nomeLider")
            email_lider = usuario.get("emailLider")
            email_envio = usuario.get("emailEnvio", email_lider)
            empresa = usuario.get("empresa")
            token = usuario.get("token")

            if not nome_lider or not email_lider or not token:
                continue

            url_final = f"https://sistema-cadastro-flask.onrender.com/validar-token-leadertrack?token={quote(str(token))}"

            assunto = "🚀 Acesso ao LeaderTrack - The HR Key"
            corpo = f"""
            <p>Olá, <strong>{nome_lider}</strong>!</p>
            <p>Você tem acesso ao <strong>LeaderTrack</strong> - Sistema de Análise de Liderança!</p>
            <p><strong>Empresa:</strong> {empresa}</p>
            <p><strong>Link de Acesso:</strong></p>
            <p><a href="{url_final}" target="_blank" style="padding:12px 24px; background:#007bff; color:white; text-decoration:none; border-radius:8px; display:inline-block;">🎯 Acessar LeaderTrack</a></p>
            <p><strong>Ou copie este link:</strong></p>
            <p style="background:#f5f5f5; padding:10px; border-radius:5px; font-family:monospace;">{url_final}</p>
            <p>✅ Este link é permanente e pode ser usado quantas vezes quiser.</p>
            <p>Você terá acesso a todos os seus relatórios e análises de liderança.</p>
            <hr>
            <p style="font-size:12px;color:#777;">The HR Key | Programa de Liderança de Alta Performance</p>
            """

            msg = MIMEMultipart()
            msg["From"] = f"The HR Key <{remetente}>"
            msg["To"] = email_envio
            msg["Subject"] = assunto
            msg.attach(MIMEText(corpo, "html"))

            with smtplib.SMTP_SSL(smtp_server, porta) as server:
                server.login(remetente, senha_remetente)
                server.sendmail(remetente, email_envio, msg.as_string())

            enviados += 1
            print(f"✅ Email LeaderTrack enviado para {email_envio}")

        except Exception as e:
            erros += 1
            print(f"❌ Erro ao enviar para {usuario.get('emailEnvio', 'sem email')}: {e}")

    return f"✅ E-mails LeaderTrack enviados com sucesso: {enviados} | ❌ Erros: {erros}"


@app.route("/painel-admin")
def painel_admin():
    return '''
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Painel Admin - Sistema Completo</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .card {
                background: white;
                padding: 20px;
                margin: 20px 0;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .btn {
                display: inline-block;
                padding: 12px 24px;
                background: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 8px;
                margin: 5px;
            }
            .btn-danger {
                background: #dc3545;
            }
            .btn-success {
                background: #28a745;
            }
            .btn-warning {
                background: #ffc107;
                color: #000;
            }
            .section {
                border-left: 5px solid #007bff;
                padding-left: 15px;
            }
            .section-leadertrack {
                border-left-color: #28a745;
            }
        </style>
    </head>
    <body>
        <h1>🎯 Painel Admin - Sistema Completo</h1>

        <div class="card section">
            <h2>📋 Sistema de Formulários (Tokens Temporários)</h2>

            <form action="/upload" method="post" enctype="multipart/form-data" target="_blank">
                <p><strong>1. Upload da planilha Excel (Formulários)</strong></p>
                <p><em>Formato: nome, email, company, codrodada, produto, tipo, nomeLider, emailLider</em></p>
                <input type="file" name="file" accept=".xlsx" required>
                <input type="submit" value="Gerar Tokens Formulários" class="btn">
            </form>

            <p><strong>2. Listar Tokens (Formulários)</strong></p>
            <a href="/listar-tokens" target="_blank" class="btn">📑 Ver Tokens Formulários</a>

            <p><strong>3. Enviar E-mails (Formulários)</strong></p>
            <a href="/enviar-emails" target="_blank" class="btn btn-success">✉️ Enviar Links Formulários</a>

            <p><strong>4. Excluir Tokens (Formulários)</strong></p>
            <a href="/excluir-tokens" target="_blank" class="btn btn-danger">🗑️ Excluir Tokens Formulários</a>
        </div>

        <div class="card section-leadertrack">
            <h2>🎯 Sistema LeaderTrack (Tokens Permanentes)</h2>

            <form action="/upload-leadertrack" method="post" enctype="multipart/form-data" target="_blank">
                <p><strong>1. Upload da planilha Excel (LeaderTrack)</strong></p>
                <p><em>Formato: nomeLider, emailLider, company, codrodada</em></p>
                <input type="file" name="file" accept=".xlsx" required>
                <input type="submit" value="Gerar Tokens LeaderTrack" class="btn btn-warning">
            </form>

            <p><strong>2. Listar Tokens (LeaderTrack)</strong></p>
            <a href="/listar-tokens-leadertrack" target="_blank" class="btn btn-warning">📑 Ver Tokens LeaderTrack</a>

            <p><strong>3. Enviar E-mails (LeaderTrack)</strong></p>
            <a href="/enviar-emails-leadertrack" target="_blank" class="btn btn-success">✉️ Enviar Links LeaderTrack</a>

            <p><strong>4. Excluir Tokens (LeaderTrack)</strong></p>
            <a href="/excluir-tokens-leadertrack" target="_blank" class="btn btn-danger">🗑️ Excluir Tokens LeaderTrack</a>
        </div>
    </body>
    </html>
    '''


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
