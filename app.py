
import streamlit as st
import sqlite3
import pandas as pd
from hashlib import sha256
from datetime import datetime
import matplotlib.pyplot as plt
import tempfile

# DB Setup
conn = sqlite3.connect("users.db", check_same_thread=False)
c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    salary REAL
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount REAL,
    category TEXT,
    description TEXT,
    date TEXT
)
''')

conn.commit()

def hash_password(pw):
    return sha256(pw.encode()).hexdigest()

def register_user(username, password, salary):
    try:
        c.execute("INSERT INTO users (username, password, salary) VALUES (?, ?, ?)", (username, hash_password(password), salary))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def login_user(username, password):
    c.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, hash_password(password)))
    return c.fetchone()

def get_user_salary(user_id):
    c.execute("SELECT salary FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    return row[0] if row else 0

def main():
    st.set_page_config(page_title="Budget App", layout="centered")
    st.title("💰 Budget-App")

    menu = ["Se connecter", "Créer un compte"]
    choice = st.sidebar.selectbox("Menu", menu)

    if "user_id" not in st.session_state:
        st.session_state.user_id = None

    if choice == "Créer un compte":
        st.subheader("Créer un nouveau compte")
        new_user = st.text_input("Nom d'utilisateur")
        new_pass = st.text_input("Mot de passe", type="password")
        salaire = st.number_input("💶 Votre salaire mensuel (€)", min_value=0.0, step=10.0)
        if st.button("S'inscrire"):
            if register_user(new_user, new_pass, salaire):
                st.success("Utilisateur créé. Connectez-vous.")
            else:
                st.error("Nom d'utilisateur déjà pris.")

    elif choice == "Se connecter":
        st.subheader("Connexion")
        user = st.text_input("Nom d'utilisateur")
        passwd = st.text_input("Mot de passe", type="password")
        if st.button("Connexion"):
            user_data = login_user(user, passwd)
            if user_data:
                st.session_state.user_id = user_data[0]
                st.success("Connecté !")
            else:
                st.error("Identifiants incorrects")

    if st.session_state.user_id:
        st.sidebar.success("Connecté")
        tab = st.sidebar.radio("Navigation", ["➕ Ajouter dépense", "📊 Tableau de bord", "📤 Export Excel", "🚪 Déconnexion"])

        if tab == "➕ Ajouter dépense":
            st.subheader("Ajouter une dépense")
            amount = st.number_input("Montant (€)", step=0.5)
            cat = st.selectbox("Catégorie", ["Alimentation", "Logement", "Transports", "Santé", "Loisirs", "Autres"])
            desc = st.text_input("Description")
            if st.button("Ajouter"):
                date_str = datetime.today().strftime('%Y-%m-%d')
                c.execute("INSERT INTO expenses (user_id, amount, category, description, date) VALUES (?, ?, ?, ?, ?)",
                          (st.session_state.user_id, amount, cat, desc, date_str))
                conn.commit()
                st.success("Dépense ajoutée ✅")

        elif tab == "📊 Tableau de bord":
            st.subheader("📈 Vos dépenses")
            c.execute("SELECT date, amount, category, description FROM expenses WHERE user_id = ? ORDER BY date DESC", (st.session_state.user_id,))
            df = pd.DataFrame(c.fetchall(), columns=["Date", "Montant", "Catégorie", "Description"])
            if not df.empty:
                st.dataframe(df)
                total_dep = df["Montant"].sum()
                salaire = get_user_salary(st.session_state.user_id)
                st.info(f"💶 Salaire déclaré : {salaire:.2f} €")
                st.success(f"💰 Total des dépenses : {total_dep:.2f} €")
                if total_dep > salaire:
                    st.error("🚨 Alerte : Vous avez dépassé votre budget mensuel !")
                pie_data = df.groupby("Catégorie")["Montant"].sum()
                fig1, ax1 = plt.subplots()
                ax1.pie(pie_data, labels=pie_data.index, autopct="%.1f%%")
                ax1.axis("equal")
                st.pyplot(fig1)
            else:
                st.warning("Aucune dépense enregistrée.")

        elif tab == "📤 Export Excel":
            st.subheader("Exporter vos dépenses")
            c.execute("SELECT date, amount, category, description FROM expenses WHERE user_id = ?", (st.session_state.user_id,))
            data = c.fetchall()
            if data:
                df = pd.DataFrame(data, columns=["Date", "Montant", "Catégorie", "Description"])
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
                    df.to_excel(tmp.name, index=False)
                    with open(tmp.name, "rb") as f:
                        st.download_button("📥 Télécharger Excel", data=f, file_name="depenses.xlsx")
            else:
                st.info("Aucune donnée à exporter.")

        elif tab == "🚪 Déconnexion":
            st.session_state.user_id = None
            st.experimental_rerun()

if __name__ == "__main__":
    main()
