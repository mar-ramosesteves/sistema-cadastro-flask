import os
import json
import unicodedata
from flask import Flask, request, render_template, redirect
from datetime import datetime, timedelta
from urllib.parse import urlencode
from urllib.parse import quote

import pandas as pd
import uuid
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = Flask(__name__)

TOKENS_FILE = os.path.join(os.path.dirname(__file__), "tokens.json")
LEADER_TRACK_TOKENS_FILE = os.path.join(os.path.dirname(__file__), "leader_track_tokens.json")  # ← ADICIONAR ESTA LINHA


# Função para normalizar textos (sem acento, minúsculo)
def normalizar(texto):
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII').strip().lower()

def carregar_tokens():
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

def carregar_leader_track_tokens():
    try:
        with open(LEADER_TRACK_TOKENS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
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

    produto = normalizar(usuario["produto"])
    tipo = normalizar(usuario["tipo"])

    if produto == "arquetipos":
        if tipo == "Autoavaliação":
            url_base = "https://gestor.thehrkey.tech/form_arquetipos_autoaval"
        elif tipo == "Avaliação Equipe":
            url_base = "https://gestor.thehrkey.tech/form_arquetipos"
        else:
            print(f"⚠️ Tipo inválido para arquétipos: {tipo}")
            return
    elif produto == "microambiente":
        if tipo in ["microambiente_equipe", "microambiente_autoavaliacao"]:
            url_base = "https://gestor.thehrkey.tech/microambiente-de-equipes"
        else:
            print(f"⚠️ Tipo inválido para microambiente: {tipo}")
            return
    else:
        print(f"⚠️ Produto inválido: {produto}")
        return


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
                    "produto": row.get("produto", "").strip(),
                    "tipo": row.get("tipo", "").strip(),
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

@app.route("/enviar-emails", methods=["GET"])
def enviar_emails():
    tokens = carregar_tokens()
    enviados = 0

    for usuario in tokens:
        try:
            nome = usuario.get("nome")
            email = usuario.get("email")
            produto = normalizar(usuario.get("produto", ""))
            tipo = normalizar(usuario.get("tipo", ""))
            token = usuario.get("token")

            if not nome or not email or not token:
                continue

            if produto == "arquetipos":
                if tipo == "autoavaliacao":
                    url_base = "https://gestor.thehrkey.tech/form_arquetipos_autoaval"
                elif tipo == "avaliacao equipe":
                    url_base = "https://gestor.thehrkey.tech/form_arquetipos"
                else:
                    continue
            elif produto == "microambiente":
                if tipo in ["microambiente_autoavaliacao", "microambiente_equipe"]:
                    url_base = "https://gestor.thehrkey.tech/microambiente-de-equipes"
                else:
                    continue
            else:
                continue

            from urllib.parse import urlencode

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

            remetente = "marramosesteves@gmail.com"
            senha_remetente = "ndlo pgyo wclq iywp"  # senha de app do Gmail
            smtp_server = "smtp.gmail.com"
            porta = 465

            msg = MIMEMultipart()
            msg["From"] = remetente
            msg["To"] = email
            msg["Subject"] = assunto
            msg.attach(MIMEText(corpo, "html"))

            with smtplib.SMTP_SSL(smtp_server, porta) as server:
                server.login(remetente, senha_remetente)
                server.sendmail(remetente, email, msg.as_string())

            enviados += 1
        except Exception as e:
            print(f"❌ Erro ao enviar para {email}: {e}")

    return f"✅ E-mails enviados com sucesso: {enviados}"

    
# ===== NOVAS ROTAS PARA LEADERTRACK =====

@app.route("/validar-token-leadertrack")
def validar_token_leadertrack():
    token_recebido = request.args.get("token")
    tokens = carregar_leader_track_tokens()
    usuario = next((t for t in tokens if t.get("token") == token_recebido), None)

    if not usuario:
        return "❌ Token inválido ou não encontrado", 404
    
    # Para LeaderTrack, não verificamos expiração nem uso
    # Apenas validamos se o token existe
    
    # Armazenar dados do usuário na sessão
    session['email_lider'] = usuario.get("emailLider")
    session['empresa'] = usuario.get("empresa")
    session['nome_lider'] = usuario.get("nomeLider")
    
    # Redirecionar para o LeaderTrack
    return redirect("https://gestor.thehrkey.tech/sistema-de-analise/")

@app.route("/upload-leadertrack", methods=["GET", "POST"])
def upload_excel_leadertrack():
    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            return "❌ Nenhum arquivo enviado.", 400

        try:
            df = pd.read_excel(file)
            tokens = carregar_leader_track_tokens()  # Carregar tokens existentes

            for _, row in df.iterrows():
                # Verificar se já existe token para este emailLider
                email_lider = row.get("emailLider", "").strip()
                token_existente = next((t for t in tokens if t.get("emailLider") == email_lider), None)
                
                if token_existente:
                    print(f"⚠️ Token já existe para {email_lider}, pulando...")
                    continue
                
                # Se não informar emailEnvio, usar emailLider como padrão
                email_envio = row.get("emailEnvio", "").strip()
                if not email_envio:
                    email_envio = email_lider
                
                token = {
                    "nomeLider": row.get("nomeLider", "").strip(),
                    "emailLider": email_lider,
                    "emailEnvio": email_envio,
                    "empresa": row.get("company", "").strip(),
                    "codrodada": row.get("codrodada", "").strip(),
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
    <h2>�� Upload de Planilha Excel para Gerar Tokens LeaderTrack</h2>
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
            f"<b>Nome do Líder:</b> {t['nomeLider']}",
            f"<b>Email do Líder:</b> {t['emailLider']}",
            f"<b>Email de Envio:</b> {t.get('emailEnvio', t['emailLider'])}",
            f"<b>Empresa:</b> {t['empresa']}",
            f"<b>Rodada:</b> {t['codrodada']}",
            f"<b>Token:</b> <code>{t['token']}</code>",
            f"<b>Criado em:</b> {t['criado_em']}",
            f"<b>Ativo:</b> {t['ativo']}"
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

    for usuario in tokens:
        try:
            nome_lider = usuario.get("nomeLider")
            email_lider = usuario.get("emailLider")
            email_envio = usuario.get("emailEnvio", email_lider)  # Usar emailEnvio se existir, senão emailLider
            empresa = usuario.get("empresa")
            token = usuario.get("token")

            if not nome_lider or not email_lider or not token:
                continue

            # URL do LeaderTrack com token
            url_final = f"https://sistema-cadastro-flask.onrender.com/validar-token-leadertrack?token={token}"

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
            <p>📊 Você terá acesso a todos os seus relatórios e análises de liderança.</p>
            <hr>
            <p style="font-size:12px;color:#777;">The HR Key | Programa de Liderança de Alta Performance</p>
            """

            remetente = "marramosesteves@gmail.com"
            senha_remetente = "ndlo pgyo wclq iywp"
            smtp_server = "smtp.gmail.com"
            porta = 465

            msg = MIMEMultipart()
            msg["From"] = remetente
            msg["To"] = email_lider
            msg["Subject"] = assunto
            msg.attach(MIMEText(corpo, "html"))

            with smtplib.SMTP_SSL(smtp_server, porta) as server:
                server.login(remetente, senha_remetente)
                server.sendmail(remetente, email_lider, msg.as_string())

            enviados += 1
            print(f"✅ Email LeaderTrack enviado para {email_lider}")
        except Exception as e:
            print(f"❌ Erro ao enviar para {email_lider}: {e}")

    return f"✅ E-mails LeaderTrack enviados com sucesso: {enviados}"

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
