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
    
    # Relacionamentos
    pacientes = db.relationship('Paciente', backref='psicologo', lazy=True)
    sessoes = db.relationship('Sessao', backref='psicologo', lazy=True)
    
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
    
    # Relacionamentos
    sessoes = db.relationship('Sessao', backref='paciente', lazy=True)
    evolucoes = db.relationship('Evolucao', backref='paciente', lazy=True)

class Sessao(db.Model):
    __tablename__ = 'sessoes'
    
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    psicologo_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    data_sessao = db.Column(db.DateTime, nullable=False)
    duracao = db.Column(db.Integer, default=50)  # em minutos
    valor = db.Column(db.Numeric(10, 2))
    status = db.Column(db.String(20), default='agendada')  # agendada, realizada, cancelada
    observacoes = db.Column(db.Text)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

class Evolucao(db.Model):
    __tablename__ = 'evolucoes'
    
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    data_evolucao = db.Column(db.DateTime, default=datetime.utcnow)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(50), default='evolucao')  # evolucao, observacao, meta

# Rotas da aplicação
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        
        usuario = Usuario.query.filter_by(email=email).first()
        
        if usuario and usuario.check_password(senha) and usuario.ativo:
            login_user(usuario)
            return redirect(url_for('dashboard'))
        else:
            flash('Email ou senha inválidos', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Estatísticas básicas
    total_pacientes = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).count()
    sessoes_hoje = Sessao.query.filter_by(
        psicologo_id=current_user.id
    ).filter(
        db.func.date(Sessao.data_sessao) == date.today()
    ).count()
    
    # Próximas sessões
    proximas_sessoes = Sessao.query.filter_by(
        psicologo_id=current_user.id,
        status='agendada'
    ).filter(
        Sessao.data_sessao >= datetime.now()
    ).order_by(Sessao.data_sessao).limit(5).all()
    
    return render_template('dashboard.html', 
                         total_pacientes=total_pacientes,
                         sessoes_hoje=sessoes_hoje,
                         proximas_sessoes=proximas_sessoes)

@app.route('/pacientes')
@login_required
def pacientes():
    pacientes = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).all()
    return render_template('pacientes.html', pacientes=pacientes)

@app.route('/pacientes/novo', methods=['GET', 'POST'])
@login_required
def novo_paciente():
    if request.method == 'POST':
        paciente = Paciente(
            nome=request.form['nome'],
            email=request.form.get('email'),
            telefone=request.form.get('telefone'),
            data_nascimento=datetime.strptime(request.form['data_nascimento'], '%Y-%m-%d').date() if request.form.get('data_nascimento') else None,
            endereco=request.form.get('endereco'),
            observacoes=request.form.get('observacoes'),
            psicologo_id=current_user.id
        )
        
        db.session.add(paciente)
        db.session.commit()
        
        flash('Paciente cadastrado com sucesso!', 'success')
        return redirect(url_for('pacientes'))
    
    return render_template('novo_paciente.html')

@app.route('/pacientes/<int:id>')
@login_required
def detalhes_paciente(id):
    paciente = Paciente.query.filter_by(id=id, psicologo_id=current_user.id).first_or_404()
    sessoes = Sessao.query.filter_by(paciente_id=id).order_by(Sessao.data_sessao.desc()).all()
    evolucoes = Evolucao.query.filter_by(paciente_id=id).order_by(Evolucao.data_evolucao.desc()).all()
    
    return render_template('detalhes_paciente.html', 
                         paciente=paciente, 
                         sessoes=sessoes,
                         evolucoes=evolucoes)

@app.route('/sessoes')
@login_required
def sessoes():
    sessoes = Sessao.query.filter_by(psicologo_id=current_user.id).order_by(Sessao.data_sessao.desc()).all()
    return render_template('sessoes.html', sessoes=sessoes)

@app.route('/sessoes/nova', methods=['GET', 'POST'])
@login_required
def nova_sessao():
    if request.method == 'POST':
        sessao = Sessao(
            paciente_id=request.form['paciente_id'],
            psicologo_id=current_user.id,
            data_sessao=datetime.strptime(request.form['data_sessao'], '%Y-%m-%dT%H:%M'),
            duracao=int(request.form.get('duracao', 50)),
            valor=float(request.form['valor']) if request.form.get('valor') else None,
            observacoes=request.form.get('observacoes')
        )
        
        db.session.add(sessao)
        db.session.commit()
        
        flash('Sessão agendada com sucesso!', 'success')
        return redirect(url_for('sessoes'))
    
    pacientes = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).all()
    return render_template('nova_sessao.html', pacientes=pacientes)

@app.route('/evolucoes/nova/<int:paciente_id>', methods=['POST'])
@login_required
def nova_evolucao(paciente_id):
    paciente = Paciente.query.filter_by(id=paciente_id, psicologo_id=current_user.id).first_or_404()
    
    evolucao = Evolucao(
        paciente_id=paciente_id,
        titulo=request.form['titulo'],
        descricao=request.form['descricao'],
        tipo=request.form.get('tipo', 'evolucao')
    )
    
    db.session.add(evolucao)
    db.session.commit()
    
    flash('Evolução registrada com sucesso!', 'success')
    return redirect(url_for('detalhes_paciente', id=paciente_id))

# API Routes
@app.route('/api/pacientes')
@login_required
def api_pacientes():
    pacientes = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).all()
    return jsonify([{
        'id': p.id,
        'nome': p.nome,
        'email': p.email,
        'telefone': p.telefone
    } for p in pacientes])

# Função para criar tabelas e usuário admin
def criar_dados_iniciais():
    with app.app_context():
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

if __name__ == '__main__':
    criar_dados_iniciais()
    app.run(debug=True)
