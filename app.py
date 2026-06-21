import os
import json
import unicodedata
import uuid
import smtplib
import ssl
from datetime import datetime, timedelta
from urllib.parse import urlencode, quote
from html import escape

import pandas as pd
from flask import Flask, request, render_template, redirect, session
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = 'sistema-cadastro-secret-key-2024'

TOKENS_FILE = os.path.join(os.path.dirname(__file__), "tokens.json")
LEADER_TRACK_TOKENS_FILE = os.path.join(os.path.dirname(__file__), "leader_track_tokens.json")
PORTAL_DESEMPENHO_USUARIOS_FILE = os.path.join(os.path.dirname(__file__), "portal_desempenho_usuarios.json")


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


def carregar_portal_desempenho_usuarios():
    if not os.path.exists(PORTAL_DESEMPENHO_USUARIOS_FILE):
        print(f"📁 Criando arquivo: {PORTAL_DESEMPENHO_USUARIOS_FILE}")
        with open(PORTAL_DESEMPENHO_USUARIOS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2, ensure_ascii=False)

    try:
        with open(PORTAL_DESEMPENHO_USUARIOS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"📥 Carregando usuários do Portal de Desempenho: {len(data)} encontrados")
            if isinstance(data, list) and all(isinstance(item, dict) for item in data):
                return data
            else:
                print("❌ ERRO: portal_desempenho_usuarios.json não está no formato esperado.")
                return []
    except Exception as e:
        print(f"❌ ERRO ao carregar usuários do Portal de Desempenho: {e}")
        return []


def salvar_portal_desempenho_usuarios(usuarios):
    with open(PORTAL_DESEMPENHO_USUARIOS_FILE, "w", encoding="utf-8") as f:
        json.dump(usuarios, f, indent=2, ensure_ascii=False)


def ler_planilha_usuarios_portal(file):
    nome_arquivo = (file.filename or "").lower()

    if nome_arquivo.endswith(".csv"):
        try:
            return pd.read_csv(file, dtype=str, encoding="utf-8-sig").fillna("")
        except UnicodeDecodeError:
            file.seek(0)
            return pd.read_csv(file, dtype=str, encoding="latin1").fillna("")

    return pd.read_excel(file, dtype=str).fillna("")


def limpar_email(email):
    return str(email or "").strip().lower()


def obter_config_email():
    remetente = "marceloesteves@thehrkey.tech"
    senha_remetente = "1Tub@r@o110368"
    smtp_server = "smtp.titan.email"
    porta = 587
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
    logs = []

    logs.append(f"📦 Total de tokens carregados: {len(tokens)}")
    logs.append(f"📨 Remetente configurado: {remetente}")
    logs.append(f"🌐 SMTP: {smtp_server}:{porta}")

    for i, usuario in enumerate(tokens, start=1):
        try:
            nome = str(usuario.get("nome", "")).strip()
            email = str(usuario.get("email", "")).strip()
            produto = normalizar(usuario.get("produto", ""))
            tipo = normalizar(usuario.get("tipo", ""))
            token = str(usuario.get("token", "")).strip()

            logs.append(f"--- Registro {i} ---")
            logs.append(f"nome={nome}")
            logs.append(f"email={email}")
            logs.append(f"produto={produto}")
            logs.append(f"tipo={tipo}")
            logs.append(f"token={'ok' if token else 'vazio'}")

            if not nome or not email or not token:
                logs.append("⏭️ Pulado: faltando nome, email ou token")
                pulados += 1
                continue

            if produto == "arquetipos":
                if tipo in ["autoavaliacao", "autoavaliacao "]:
                    url_base = "https://gestor.thehrkey.tech/form_arquetipos_autoaval"
                elif tipo in ["avaliacao equipe", "avaliacao de equipe"]:
                    url_base = "https://gestor.thehrkey.tech/form_arquetipos"
                else:
                    logs.append(f"⏭️ Pulado: tipo inválido para arquétipos -> {tipo}")
                    pulados += 1
                    continue

            elif produto == "microambiente":
                if tipo in ["microambiente_autoavaliacao", "microambiente autoavaliacao"]:
                    url_base = "https://gestor.thehrkey.tech/microambiente-de-equipes"
                elif tipo in ["microambiente_equipe", "microambiente equipe"]:
                    url_base = "https://gestor.thehrkey.tech/microambiente-de-equipes"
                else:
                    logs.append(f"⏭️ Pulado: tipo inválido para microambiente -> {tipo}")
                    pulados += 1
                    continue
            else:
                logs.append(f"⏭️ Pulado: produto inválido -> {produto}")
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

            with smtplib.SMTP(smtp_server, porta) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
                server.login(remetente, senha_remetente)
                server.sendmail(remetente, email, msg.as_string())

            enviados += 1
            logs.append(f"✅ Enviado com sucesso para {email}")

        except Exception as e:
            erros += 1
            logs.append(f"❌ Erro ao enviar para {usuario.get('email', 'sem email')}: {str(e)}")

    resumo = f"✅ Enviados: {enviados} | ⏭️ Pulados: {pulados} | ❌ Erros: {erros} | 📦 Total: {len(tokens)}"
    return f"<pre>{resumo}\n\n" + "\n".join(logs) + "</pre>"


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
    logs = []

    remetente, senha_remetente, smtp_server, porta = obter_config_email()

    logs.append(f"📦 Total de tokens LeaderTrack carregados: {len(tokens)}")
    logs.append(f"📨 Remetente configurado: {remetente}")
    logs.append(f"🌐 SMTP: {smtp_server}:{porta}")

    for i, usuario in enumerate(tokens, start=1):
        try:
            nome_lider = usuario.get("nomeLider")
            email_lider = usuario.get("emailLider")
            email_envio = usuario.get("emailEnvio", email_lider)
            empresa = usuario.get("empresa")
            token = usuario.get("token")

            logs.append(f"--- Registro LeaderTrack {i} ---")
            logs.append(f"nomeLider={nome_lider}")
            logs.append(f"emailEnvio={email_envio}")
            logs.append(f"empresa={empresa}")
            logs.append(f"token={'ok' if token else 'vazio'}")

            if not nome_lider or not email_lider or not token:
                logs.append("⏭️ Pulado: faltando nomeLider, emailLider ou token")
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

            with smtplib.SMTP(smtp_server, porta) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
                server.login(remetente, senha_remetente)
                server.sendmail(remetente, email_envio, msg.as_string())

            enviados += 1
            logs.append(f"✅ Email LeaderTrack enviado para {email_envio}")

        except Exception as e:
            erros += 1
            logs.append(f"❌ Erro ao enviar para {usuario.get('emailEnvio', 'sem email')}: {str(e)}")

    resumo = f"✅ E-mails LeaderTrack enviados com sucesso: {enviados} | ❌ Erros: {erros} | 📦 Total: {len(tokens)}"
    return f"<pre>{resumo}\n\n" + "\n".join(logs) + "</pre>"


@app.route("/upload-portal-desempenho", methods=["GET", "POST"])
def upload_portal_desempenho():
    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            return "❌ Nenhum arquivo enviado.", 400

        try:
            df = ler_planilha_usuarios_portal(file)

            colunas = set(df.columns)
            if "user_email" not in colunas and "email" not in colunas:
                return "❌ A planilha precisa ter a coluna user_email ou email.", 400

            usuarios = []
            emails_vistos = set()
            pulados = 0

            for _, row in df.iterrows():
                email = limpar_email(row.get("user_email", row.get("email", "")))

                if not email or "@" not in email:
                    pulados += 1
                    continue

                if email in emails_vistos:
                    pulados += 1
                    continue

                emails_vistos.add(email)

                first_name = str(row.get("first_name", "")).strip()
                display_name = str(row.get("display_name", "")).strip()

                if not display_name:
                    display_name = first_name or email.split("@")[0]

                if not first_name:
                    first_name = display_name.split(" ")[0] if display_name else "Olá"

                usuarios.append({
                    "user_email": email,
                    "first_name": first_name,
                    "display_name": display_name,
                    "carregado_em": datetime.now().isoformat(),
                    "enviado": False,
                    "enviado_em": None,
                    "erro": None
                })

            salvar_portal_desempenho_usuarios(usuarios)

            return (
                f"✅ Lista do Portal de Desempenho carregada com sucesso!<br>"
                f"📦 Usuários válidos carregados: {len(usuarios)}<br>"
                f"⏭️ Registros pulados: {pulados}<br><br>"
                f"<a href='/listar-usuarios-portal-desempenho'>Ver usuários carregados</a>"
            )

        except Exception as e:
            return f"❌ Erro ao processar arquivo: {e}", 500

    return """
    <!doctype html>
    <title>Upload - Portal de Avaliação de Desempenho</title>
    <h2>📊 Upload de CSV/Excel - Portal de Avaliação de Desempenho</h2>
    <p><strong>Formato esperado:</strong> user_email, first_name, display_name</p>
    <p><em>Também aceita o CSV completo do WordPress, desde que tenha user_email.</em></p>
    <form method="post" enctype="multipart/form-data">
      <input type="file" name="file" accept=".csv,.xlsx" required>
      <input type="submit" value="Carregar Usuários do Portal">
    </form>
    """


@app.route("/listar-usuarios-portal-desempenho")
def listar_usuarios_portal_desempenho():
    usuarios = carregar_portal_desempenho_usuarios()

    html = "<h2>✅ USUÁRIOS CARREGADOS - PORTAL DE AVALIAÇÃO DE DESEMPENHO</h2>"
    html += f"<p><strong>Total:</strong> {len(usuarios)}</p>"
    html += "<ul style='font-family:monospace;'>"

    for u in usuarios:
        status_envio = "✅ Enviado" if u.get("enviado") else "⏳ Pendente"
        erro = u.get("erro") or ""
        html += "<li>"
        html += "<br>".join([
            f"<b>Nome:</b> {escape(str(u.get('display_name', '')))}",
            f"<b>Email:</b> {escape(str(u.get('user_email', '')))}",
            f"<b>Status:</b> {status_envio}",
            f"<b>Enviado em:</b> {escape(str(u.get('enviado_em') or ''))}",
            f"<b>Erro:</b> {escape(str(erro))}"
        ])
        html += "</li><hr>"

    html += "</ul>"
    return html


@app.route("/excluir-usuarios-portal-desempenho", methods=["GET", "POST"])
def excluir_usuarios_portal_desempenho():
    if request.method == "POST":
        try:
            salvar_portal_desempenho_usuarios([])
            return "✅ Todos os usuários carregados do Portal de Desempenho foram excluídos com sucesso!"
        except Exception as e:
            return f"❌ Erro ao excluir usuários carregados: {e}"

    return """
        <h2>Confirmação de Exclusão - Portal de Avaliação de Desempenho</h2>
        <p style="color:red;"><strong>ATENÇÃO:</strong> Esta ação vai apagar apenas a lista carregada para envio de e-mails do portal. Ela não apaga usuários do WordPress nem do Supabase.</p>
        <form method="post">
            <button type="submit" style="padding:10px 20px; background:red; color:white; border:none; border-radius:8px;">Excluir lista carregada</button>
        </form>
        <p><a href="/listar-usuarios-portal-desempenho">Voltar</a></p>
    """


@app.route("/enviar-emails-portal-desempenho", methods=["GET"])
def enviar_emails_portal_desempenho():
    usuarios = carregar_portal_desempenho_usuarios()

    remetente, senha_remetente, smtp_server, porta = obter_config_email()

    enviados = 0
    pulados = 0
    erros = 0
    logs = []

    portal_url = "https://gestor.thehrkey.tech/meu-portal-leadertrack/"
    criar_senha_url = "https://gestor.thehrkey.tech/wp-login.php?action=lostpassword"
    login_portal_url = "https://gestor.thehrkey.tech/wp-login.php?redirect_to=https%3A%2F%2Fgestor.thehrkey.tech%2Fmeu-portal-leadertrack%2F"

    logs.append(f"📦 Total de usuários carregados: {len(usuarios)}")
    logs.append(f"📨 Remetente configurado: {remetente}")
    logs.append(f"🌐 SMTP: {smtp_server}:{porta}")

    for i, usuario in enumerate(usuarios, start=1):
        try:
            nome = str(usuario.get("first_name") or usuario.get("display_name") or "Olá").strip()
            nome_completo = str(usuario.get("display_name") or nome).strip()
            email = limpar_email(usuario.get("user_email", ""))

            logs.append(f"--- Registro Portal {i} ---")
            logs.append(f"nome={nome_completo}")
            logs.append(f"email={email}")

            if usuario.get("enviado"):
                logs.append("⏭️ Pulado: e-mail já marcado como enviado anteriormente")
                pulados += 1
                continue

            if not email or "@" not in email:
                logs.append("⏭️ Pulado: e-mail inválido")
                pulados += 1
                continue

            assunto = "Acesso ao Portal LeaderTrack - Avaliação de Desempenho"

            corpo = f"""
            <div style="font-family:Arial,sans-serif; color:#1f2937; line-height:1.6;">
              <p>Olá, <strong>{escape(nome)}</strong>!</p>

              <p>Seu acesso ao <strong>Portal LeaderTrack</strong> já está disponível.</p>

              <p><strong>Para acessar pela primeira vez:</strong></p>

              <ol>
                <li>Use como <strong>usuário</strong> o seu próprio e-mail cadastrado: <strong>{escape(email)}</strong>.</li>
                <li>Clique no botão <strong>“Criar minha senha”</strong>.</li>
                <li>Informe novamente o seu e-mail cadastrado.</li>
                <li>O sistema enviará um e-mail com o link para criação da sua senha.</li>
                <li>Depois de criar a senha, volte a este e-mail e clique em <strong>“Acessar Portal LeaderTrack”</strong>.</li>
              </ol>

              <p>
                <a href="{criar_senha_url}" target="_blank" style="padding:12px 24px; background:#111827; color:white; text-decoration:none; border-radius:8px; display:inline-block; margin-right:8px;">
                  Criar minha senha
                </a>

                <a href="{login_portal_url}" target="_blank" style="padding:12px 24px; background:#007bff; color:white; text-decoration:none; border-radius:8px; display:inline-block;">
                  Acessar Portal LeaderTrack
                </a>
              </p>

              <p><strong>Links para copiar, se necessário:</strong></p>
              <p><strong>Criar senha:</strong></p>
              <p style="background:#f5f5f5; padding:10px; border-radius:5px; font-family:monospace;">{criar_senha_url}</p>
              <p><strong>Acessar Portal:</strong></p>
              <p style="background:#f5f5f5; padding:10px; border-radius:5px; font-family:monospace;">{login_portal_url}</p>

              <p style="background:#fff7ed; border-left:4px solid #f97316; padding:12px; border-radius:6px;">
                <strong>Importante:</strong> o e-mail de redefinição de senha pode cair na caixa de
                <strong>Spam</strong>, <strong>Lixo eletrônico</strong>, <strong>Promoções</strong> ou similar.
                Caso não encontre na caixa de entrada, verifique essas pastas.
              </p>

              <p>No portal, você verá os módulos disponíveis conforme seu perfil de acesso.</p>

              <p>Em caso de dificuldade, entre em contato com o RH ou com o responsável pelo projeto LeaderTrack.</p>

              <hr>
              <p style="font-size:12px;color:#777;">The HR Key | LeaderTrack | Avaliação de Desempenho</p>
            </div>
            """

            msg = MIMEMultipart()
            msg["From"] = f"The HR Key <{remetente}>"
            msg["To"] = email
            msg["Subject"] = assunto
            msg.attach(MIMEText(corpo, "html"))

            with smtplib.SMTP(smtp_server, porta) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
                server.login(remetente, senha_remetente)
                server.sendmail(remetente, email, msg.as_string())

            usuario["enviado"] = True
            usuario["enviado_em"] = datetime.now().isoformat()
            usuario["erro"] = None
            enviados += 1
            logs.append(f"✅ E-mail do Portal enviado para {email}")

        except Exception as e:
            erros += 1
            usuario["erro"] = str(e)
            logs.append(f"❌ Erro ao enviar para {usuario.get('user_email', 'sem email')}: {str(e)}")

    salvar_portal_desempenho_usuarios(usuarios)

    resumo = f"✅ E-mails Portal enviados: {enviados} | ⏭️ Pulados: {pulados} | ❌ Erros: {erros} | 📦 Total: {len(usuarios)}"
    return f"<pre>{resumo}\n\n" + "\n".join(logs) + "</pre>"


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
            .section-portal {
                border-left-color: #6f42c1;
            }
            .btn-purple {
                background: #6f42c1;
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

        <div class="card section-portal">
            <h2>🧭 Portal de Avaliação de Desempenho</h2>

            <form action="/upload-portal-desempenho" method="post" enctype="multipart/form-data" target="_blank">
                <p><strong>1. Upload da lista de usuários do portal</strong></p>
                <p><em>Formato esperado: user_email, first_name, display_name</em></p>
                <p><em>Este envio não gera token. Ele apenas envia a orientação de primeiro acesso ao portal.</em></p>
                <input type="file" name="file" accept=".csv,.xlsx" required>
                <input type="submit" value="Carregar Usuários do Portal" class="btn btn-purple">
            </form>

            <p><strong>2. Listar usuários carregados</strong></p>
            <a href="/listar-usuarios-portal-desempenho" target="_blank" class="btn btn-purple">📑 Ver Usuários do Portal</a>

            <p><strong>3. Enviar e-mails de acesso ao Portal</strong></p>
            <a href="/enviar-emails-portal-desempenho" target="_blank" class="btn btn-success">✉️ Enviar Acessos ao Portal</a>

            <p><strong>4. Excluir lista carregada do Portal</strong></p>
            <a href="/excluir-usuarios-portal-desempenho" target="_blank" class="btn btn-danger">🗑️ Excluir Lista do Portal</a>
        </div>
    </body>
    </html>
    '''


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
