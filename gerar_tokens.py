import pandas as pd
import uuid
import json
from datetime import datetime, timedelta

# Caminhos dos arquivos
ARQUIVO_EXCEL = "cadastro_usuarios_tokens.xlsx"
ARQUIVO_TOKENS = "tokens.json"

# Leitura da planilha
df = pd.read_excel(ARQUIVO_EXCEL)

# Criação da lista de tokens
tokens = []
for _, row in df.iterrows():
    token_info = {
        "nome": row["nome"],
        "email": row["email"],
        "empresa": row["empresa"],
        "codrodada": row["codrodada"],
        "nomeLider": row["nomeLider"],
        "emailLider": row["emailLider"],
        "tipo": row["tipo"],
        "produto": "arquetipos" if "arquetipo" in row["tipo"] else "microambiente",
        "token": uuid.uuid4().hex[:10],
        "expira_em": (datetime.now() + timedelta(days=2)).isoformat(),
        "usado": False
    }
    tokens.append(token_info)

# Salva no tokens.json
with open(ARQUIVO_TOKENS, "w", encoding="utf-8") as f:
    json.dump(tokens, f, indent=2, ensure_ascii=False)

print("✅ tokens.json gerado com sucesso.")
