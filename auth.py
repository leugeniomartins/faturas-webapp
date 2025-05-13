from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import sqlite3

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']
        with sqlite3.connect('faturas.db') as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM usuarios WHERE usuario=? AND senha=?", (usuario, senha))
            user = c.fetchone()
            if user:
                session['usuario'] = usuario
                return redirect(url_for('index'))
            else:
                flash("Usuário ou senha inválidos.")
    return render_template('login.html')

@auth.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('auth.login'))

@auth.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
def editar_usuario(id):
    with sqlite3.connect('faturas.db') as conn:
        c = conn.cursor()
        if request.method == 'POST':
            nome = request.form['nome']
            usuario = request.form['usuario']
            senha = request.form['senha']
            try:
                c.execute("UPDATE usuarios SET nome=?, usuario=?, senha=? WHERE id=?", (nome, usuario, senha, id))
                conn.commit()
                return redirect('/usuarios')
            except sqlite3.IntegrityError:
                flash("Erro ao atualizar usuário.")
        c.execute("SELECT * FROM usuarios WHERE id=?", (id,))
        user = c.fetchone()
    return render_template('editar_usuario.html', user=user)

@auth.route('/usuarios/deletar/<int:id>')
def deletar_usuario(id):
    with sqlite3.connect('faturas.db') as conn:
        conn.execute("DELETE FROM usuarios WHERE id=?", (id,))
    return redirect('/usuarios')
