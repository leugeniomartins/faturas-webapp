from flask import Flask, render_template, request, redirect, send_from_directory, session, url_for, flash, send_file
import sqlite3, os
from werkzeug.utils import secure_filename
from auth import auth
import pandas as pd
import smtplib
from email.message import EmailMessage
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'chave_super_secreta'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

app.register_blueprint(auth, url_prefix='/')

# Inicializa o banco de dados com tabelas de faturas e usuários
def init_db():
    with sqlite3.connect('faturas.db') as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS faturas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fornecedor TEXT,
                tipo_servico TEXT,
                mes_ano TEXT,
                valor REAL,
                data_recebimento TEXT,
                status_pagamento TEXT,
                arquivo_nome TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT,
                usuario TEXT UNIQUE,
                senha TEXT
            )
        """)
        c.execute("INSERT OR IGNORE INTO usuarios (nome, usuario, senha) VALUES ('Administrador', 'admin', 'admin')")

@app.before_request
def checar_login():
    if not session.get('usuario') and request.endpoint not in ['auth.login', 'static']:
        return redirect(url_for('auth.login'))

@app.route('/')
def index():
    fornecedor = request.args.get('fornecedor', '')
    status = request.args.get('status', '')
    mes_ano = request.args.get('mes_ano', '')

    query = "SELECT * FROM faturas WHERE 1=1"
    params = []

    if fornecedor:
        query += " AND fornecedor LIKE ?"
        params.append(f'%{fornecedor}%')
    if status:
        query += " AND status_pagamento = ?"
        params.append(status)
    if mes_ano:
        query += " AND mes_ano = ?"
        params.append(mes_ano)

    with sqlite3.connect('faturas.db') as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        faturas = cursor.fetchall()
    return render_template('index.html', faturas=faturas)

@app.route('/nova', methods=['GET', 'POST'])
def nova():
    if request.method == 'POST':
        fornecedor = request.form['fornecedor']
        tipo_servico = request.form['tipo_servico']
        mes_ano = request.form['mes_ano']
        valor = request.form['valor']
        data_recebimento = request.form['data_recebimento']
        status_pagamento = request.form['status_pagamento']
        arquivo = request.files['arquivo']
        email = request.form.get('email', '')

        arquivo_nome = None
        if arquivo:
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            arquivo_nome = secure_filename(arquivo.filename)
            caminho_upload = os.path.join(app.config['UPLOAD_FOLDER'], arquivo_nome)
            arquivo.save(caminho_upload)

        with sqlite3.connect('faturas.db') as conn:
            conn.execute("""
                INSERT INTO faturas (fornecedor, tipo_servico, mes_ano, valor, data_recebimento, status_pagamento, arquivo_nome)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (fornecedor, tipo_servico, mes_ano, valor, data_recebimento, status_pagamento, arquivo_nome))

        # Enviar e-mail com anexo se o campo email for preenchido
        if email and arquivo_nome:
            enviar_email_com_anexo(email, arquivo_nome)

        return redirect('/')
    return render_template('nova.html')

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/exportar')
def exportar():
    with sqlite3.connect('faturas.db') as conn:
        df = pd.read_sql_query("SELECT * FROM faturas", conn)
    filepath = "faturas_exportadas.xlsx"
    df.to_excel(filepath, index=False)
    return send_file(filepath, as_attachment=True)

@app.route('/usuarios')
def usuarios():
    with sqlite3.connect('faturas.db') as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM usuarios")
        lista = c.fetchall()
    return render_template('usuarios.html', usuarios=lista)

@app.route('/usuarios/novo', methods=['GET', 'POST'])
def novo_usuario():
    if request.method == 'POST':
        nome = request.form['nome']
        usuario = request.form['usuario']
        senha = request.form['senha']
        with sqlite3.connect('faturas.db') as conn:
            try:
                conn.execute("INSERT INTO usuarios (nome, usuario, senha) VALUES (?, ?, ?)", (nome, usuario, senha))
                return redirect('/usuarios')
            except sqlite3.IntegrityError:
                flash('Usuário já existe.')
    return render_template('novo_usuario.html')

def enviar_email_com_anexo(destinatario, arquivo_nome):
    EMAIL_REMETENTE = "seu_email@provedor.com"
    SENHA = "sua_senha"

    msg = EmailMessage()
    msg['Subject'] = "Fatura Recebida"
    msg['From'] = EMAIL_REMETENTE
    msg['To'] = destinatario
    msg.set_content("Segue a fatura em anexo.")

    caminho = os.path.join(app.config['UPLOAD_FOLDER'], arquivo_nome)
    with open(caminho, 'rb') as f:
        dados = f.read()
        msg.add_attachment(dados, maintype='application', subtype='octet-stream', filename=arquivo_nome)

    with smtplib.SMTP_SSL('smtp.seu_provedor.com', 465) as smtp:
        smtp.login(EMAIL_REMETENTE, SENHA)
        smtp.send_message(msg)

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar_fatura(id):
    with sqlite3.connect('faturas.db') as conn:
        c = conn.cursor()
        if request.method == 'POST':
            fornecedor = request.form['fornecedor']
            tipo_servico = request.form['tipo_servico']
            mes_ano = request.form['mes_ano']
            valor = request.form['valor']
            data_recebimento = request.form['data_recebimento']
            status_pagamento = request.form['status_pagamento']
            arquivo = request.files['arquivo']

            arquivo_nome = None
            if arquivo and arquivo.filename:
                if not os.path.exists(app.config['UPLOAD_FOLDER']):
                    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                arquivo_nome = secure_filename(arquivo.filename)
                caminho_upload = os.path.join(app.config['UPLOAD_FOLDER'], arquivo_nome)
                arquivo.save(caminho_upload)
                c.execute("UPDATE faturas SET fornecedor=?, tipo_servico=?, mes_ano=?, valor=?, data_recebimento=?, status_pagamento=?, arquivo_nome=? WHERE id=?",
                          (fornecedor, tipo_servico, mes_ano, valor, data_recebimento, status_pagamento, arquivo_nome, id))
            else:
                c.execute("UPDATE faturas SET fornecedor=?, tipo_servico=?, mes_ano=?, valor=?, data_recebimento=?, status_pagamento=? WHERE id=?",
                          (fornecedor, tipo_servico, mes_ano, valor, data_recebimento, status_pagamento, id))
            conn.commit()
            return redirect('/')
        c.execute("SELECT * FROM faturas WHERE id=?", (id,))
        fatura = c.fetchone()
    return render_template('editar_fatura.html', f=fatura)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)




def is_admin():
    with sqlite3.connect('faturas.db') as conn:
        c = conn.cursor()
        c.execute("SELECT tipo FROM usuarios WHERE usuario=?", (session.get('usuario'),))
        tipo = c.fetchone()
        return tipo and tipo[0] == 'admin'

@app.route('/backup')
def backup():
    if not is_admin():
        return "Acesso restrito", 403
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"backup_faturas_{timestamp}.db"
    import shutil
    shutil.copyfile("faturas.db", backup_path)
    return send_file(backup_path, as_attachment=True)


def ajustar_usuarios_para_tipo():
    with sqlite3.connect('faturas.db') as conn:
        c = conn.cursor()
        c.execute("PRAGMA table_info(usuarios)")
        colunas = [col[1] for col in c.fetchall()]
        if "tipo" not in colunas:
            c.execute("ALTER TABLE usuarios ADD COLUMN tipo TEXT DEFAULT 'padrao'")
            c.execute("UPDATE usuarios SET tipo='admin' WHERE usuario='admin'")
            conn.commit()

ajustar_usuarios_para_tipo()