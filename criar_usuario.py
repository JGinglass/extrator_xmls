"""
Utilitário para criar / adicionar usuários no config.yaml de autenticação.
Execute uma vez antes de rodar o app:

    .venv\\Scripts\\python criar_usuario.py
"""

import getpass
import os
import sys

import bcrypt
import yaml

CONFIG_FILE = "config.yaml"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def load_config() -> dict:
    default = {
        "credentials": {"usernames": {}},
        "cookie": {
            "name": "vgr_auth",
            "key": "vgr-medical-secret-key-mude-isso",
            "expiry_days": 30,
        },
    }
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if data and "credentials" in data:
            return data
    return default


def save_config(config: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)


def main():
    print("=" * 45)
    print("  VGR Medical — Criação de usuário")
    print("=" * 45)

    config = load_config()
    users = config["credentials"]["usernames"]

    username = input("\nNome de usuário (login): ").strip()
    if not username:
        print("Usuário não pode ser vazio.")
        sys.exit(1)

    if username in users:
        sobrescrever = input(f"Usuário '{username}' já existe. Sobrescrever? (s/N): ")
        if sobrescrever.lower() != "s":
            print("Operação cancelada.")
            sys.exit(0)

    nome = input("Nome completo (exibido no app): ").strip() or username
    email = input("E-mail (opcional): ").strip()

    password = getpass.getpass("Senha: ")
    confirm = getpass.getpass("Confirme a senha: ")
    if password != confirm:
        print("As senhas não coincidem.")
        sys.exit(1)
    if len(password) < 6:
        print("Senha muito curta (mínimo 6 caracteres).")
        sys.exit(1)

    users[username] = {
        "name": nome,
        "email": email,
        "password": hash_password(password),
    }

    save_config(config)
    print(f"\n✅ Usuário '{username}' salvo em {CONFIG_FILE}")
    print("   Agora rode: .venv\\Scripts\\streamlit run app.py")


if __name__ == "__main__":
    main()
