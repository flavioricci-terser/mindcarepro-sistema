import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Configuração do banco com psycopg3
database_url = os.getenv('DATABASE_URL')
if database_url and database_url.startswith('postgresql://'):
    database_url = database_url.replace('postgresql://', 'postgresql+psycopg://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'mindcarepro-secret-key')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicialização das extensões
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# Modelos do banco de dados
class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default='psicologo')
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.senha_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.senha_hash, password)

class Paciente(db.Model):
    __tablename__ = 'pacientes'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    telefone = db.Column(db.String(20))
    data_nascimento = db.Column(db.Date)
    endereco = db.Column(db.Text)
    observacoes = db.Column(db.Text)
    ativo = db.Column(db.Boolean, default=True)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    psicologo_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)

class Sessao(db.Model):
    __tablename__ = 'sessoes'
    
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    psicologo_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    data_sessao = db.Column(db.DateTime, nullable=False)
    duracao = db.Column(db.Integer, default=50)
    valor = db.Column(db.Numeric(10, 2))
    status = db.Column(db.String(20), default='agendada')
    observacoes = db.Column(db.Text)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

class Evolucao(db.Model):
    __tablename__ = 'evolucoes'
    
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    data_evolucao = db.Column(db.DateTime, default=datetime.utcnow)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(50), default='evolucao')

# Função auxiliar para login
def processar_login():
    email = request.form.get('email', '').strip()
    senha = request.form.get('senha', '')
    
    if not email or not senha:
        flash('Email e senha são obrigatórios', 'error')
        return False
    
    usuario = Usuario.query.filter_by(email=email).first()
    
    if usuario and usuario.check_password(senha) and usuario.ativo:
        login_user(usuario)
        return True
    else:
        flash('Email ou senha inválidos', 'error')
        return False

# Rotas da aplicação
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if processar_login():
            return redirect(url_for('dashboard'))
        return render_template('login.html')
    
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if processar_login():
            return redirect(url_for('dashboard'))
        return render_template('login.html')
    
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return "<h1>Dashboard do MindCarePro</h1><p>Bem-vindo, " + current_user.nome + "!</p><a href='/logout'>Sair</a>"

# Função para criar tabelas e usuário admin
def criar_dados_iniciais():
    with app.app_context():
        try:
            db.create_all()
            
            # Verificar se já existe um usuário admin
            admin = Usuario.query.filter_by(email='admin@mindcarepro.com').first()
            if not admin:
                admin = Usuario(
                    nome='Administrador',
                    email='admin@mindcarepro.com',
                    tipo='admin'
                )
                admin.set_password('123456')
                db.session.add(admin)
                db.session.commit()
                print("Usuário admin criado: admin@mindcarepro.com / 123456")
        except Exception as e:
            print(f"Erro ao criar dados iniciais: {e}")

if __name__ == '__main__':
    criar_dados_iniciais()
    app.run(debug=True)
else:
    criar_dados_iniciais()
