import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid

# Configuração da aplicação
app = Flask(__name__)

# Configurações para Railway
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'mindcarepro-railway-secret-2025')

# Configuração do banco de dados (Railway fornece automaticamente)
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Railway PostgreSQL
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Local SQLite para desenvolvimento
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mindcarepro.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar extensões
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# =====================================================
# MODELOS DE DADOS
# =====================================================

class User(UserMixin, db.Model):
    """Modelo do usuário (psicólogo/psicanalista)"""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    nome = db.Column(db.String(100), nullable=False)
    crp = db.Column(db.String(20))
    telefone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Cliente(db.Model):
    """Modelo do cliente"""
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    telefone = db.Column(db.String(20))
    data_nascimento = db.Column(db.Date)
    profissao = db.Column(db.String(100))
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    sessoes = db.relationship('Sessao', backref='cliente', lazy=True)
    pagamentos = db.relationship('Pagamento', backref='cliente', lazy=True)

    @property
    def idade(self):
        if self.data_nascimento:
            return (datetime.now().date() - self.data_nascimento).days // 365
        return None

    @property
    def aniversario_hoje(self):
        if self.data_nascimento:
            hoje = datetime.now().date()
            return (self.data_nascimento.month == hoje.month and 
                   self.data_nascimento.day == hoje.day)
        return False

class Sessao(db.Model):
    """Modelo das sessões de terapia"""
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    data_hora = db.Column(db.DateTime, nullable=False)
    duracao = db.Column(db.Integer, default=50)  # minutos
    valor = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='agendada')
    confirmacao_cliente = db.Column(db.Boolean, default=False)
    meet_link = db.Column(db.String(200))
    meet_id = db.Column(db.String(100))
    anotacoes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Pagamento(db.Model):
    """Modelo de controle de pagamentos"""
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    sessao_id = db.Column(db.Integer, db.ForeignKey('sessao.id'))
    valor = db.Column(db.Float, nullable=False)
    data_vencimento = db.Column(db.Date, nullable=False)
    data_pagamento = db.Column(db.Date)
    metodo = db.Column(db.String(20), default='pix')
    status = db.Column(db.String(20), default='pendente')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# =====================================================
# CONFIGURAÇÃO DE LOGIN
# =====================================================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# =====================================================
# ROTAS PRINCIPAIS
# =====================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Tela de login"""
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Email ou senha incorretos', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Logout do usuário"""
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    """Dashboard principal"""
    hoje = datetime.now().date()
    
    # Sessões de hoje
    sessoes_hoje = Sessao.query.filter(
        db.func.date(Sessao.data_hora) == hoje
    ).order_by(Sessao.data_hora).all()
    
    # Aniversariantes da semana
    inicio_semana = hoje
    fim_semana = hoje + timedelta(days=7)
    
    aniversariantes = []
    clientes = Cliente.query.filter_by(ativo=True).all()
    
    for cliente in clientes:
        if cliente.data_nascimento:
            aniv_este_ano = cliente.data_nascimento.replace(year=hoje.year)
            if inicio_semana <= aniv_este_ano <= fim_semana:
                aniversariantes.append({
                    'cliente': cliente,
                    'data': aniv_este_ano,
                    'idade': cliente.idade + 1,
                    'eh_hoje': aniv_este_ano == hoje
                })
    
    # Métricas do dia
    total_sessoes = len(sessoes_hoje)
    confirmadas = len([s for s in sessoes_hoje if s.confirmacao_cliente])
    receita_dia = sum([s.valor for s in sessoes_hoje if s.status != 'cancelada'])
    
    return render_template('dashboard.html',
                         sessoes_hoje=sessoes_hoje,
                         aniversariantes=aniversariantes,
                         total_sessoes=total_sessoes,
                         confirmadas=confirmadas,
                         receita_dia=receita_dia,
                         clientes=clientes)

@app.route('/clientes')
@login_required
def clientes():
    """Lista de clientes"""
    clientes = Cliente.query.filter_by(ativo=True).order_by(Cliente.nome).all()
    return render_template('clientes.html', clientes=clientes)

@app.route('/agenda')
@login_required
def agenda():
    """Agenda semanal"""
    hoje = datetime.now().date()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    
    sessoes = Sessao.query.filter(
        db.func.date(Sessao.data_hora) >= inicio_semana,
        db.func.date(Sessao.data_hora) <= inicio_semana + timedelta(days=6)
    ).order_by(Sessao.data_hora).all()
    
    agenda_semana = {}
    for i in range(7):
        dia = inicio_semana + timedelta(days=i)
        agenda_semana[dia] = []
    
    for sessao in sessoes:
        dia = sessao.data_hora.date()
        if dia in agenda_semana:
            agenda_semana[dia].append(sessao)
    
    return render_template('agenda.html',
                         agenda_semana=agenda_semana,
                         inicio_semana=inicio_semana,
                         timedelta=timedelta)

@app.route('/financeiro')
@login_required
def financeiro():
    """Controle financeiro"""
    hoje = datetime.now().date()
    inicio_mes = hoje.replace(day=1)
    
    receita_mes = db.session.query(
        db.func.sum(Pagamento.valor)
    ).filter(
        Pagamento.status == 'pago',
        Pagamento.data_pagamento >= inicio_mes
    ).scalar() or 0
    
    pendentes = Pagamento.query.filter_by(status='pendente').all()
    atrasados = Pagamento.query.filter(
        Pagamento.status == 'pendente',
        Pagamento.data_vencimento < hoje
    ).all()
    
    return render_template('financeiro.html',
                         receita_mes=receita_mes,
                         pendentes=pendentes,
                         atrasados=atrasados)

# =====================================================
# APIs AJAX
# =====================================================

@app.route('/api/confirmar_sessao/<int:sessao_id>', methods=['POST'])
@login_required
def confirmar_sessao(sessao_id):
    """API para confirmar sessão"""
    sessao = Sessao.query.get_or_404(sessao_id)
    sessao.confirmacao_cliente = True
    sessao.status = 'confirmada'
    db.session.commit()
    return jsonify({'success': True, 'message': 'Sessão confirmada'})

@app.route('/api/gerar_meet/<int:sessao_id>', methods=['POST'])
@login_required
def gerar_meet(sessao_id):
    """API para gerar link do Google Meet"""
    sessao = Sessao.query.get_or_404(sessao_id)
    
    meet_id = str(uuid.uuid4())[:12]
    meet_link = f"https://meet.google.com/{meet_id}"
    
    sessao.meet_link = meet_link
    sessao.meet_id = meet_id
    db.session.commit()
    
    return jsonify({
        'success': True, 
        'meet_link': meet_link,
        'message': 'Link do Meet gerado'
    })

@app.route('/api/marcar_pagamento/<int:pagamento_id>', methods=['POST'])
@login_required
def marcar_pagamento(pagamento_id):
    """API para marcar pagamento como pago"""
    pagamento = Pagamento.query.get_or_404(pagamento_id)
    pagamento.status = 'pago'
    pagamento.data_pagamento = datetime.now().date()
    db.session.commit()
    return jsonify({'success': True, 'message': 'Pagamento confirmado'})

# =====================================================
# HEALTH CHECK (Railway precisa)
# =====================================================

@app.route('/health')
def health_check():
    """Health check para Railway"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

# =====================================================
# INICIALIZAÇÃO
# =====================================================

def init_db():
    """Inicializa o banco de dados com dados de exemplo"""
    with app.app_context():
        db.create_all()
        
        # Criar usuário admin se não existir
        if not User.query.first():
            admin = User(
                email='admin@mindcarepro.com',
                password_hash=generate_password_hash('123456'),
                nome='Dr. João Silva',
                crp='CRP 12345',
                telefone='(11) 99999-9999'
            )
            db.session.add(admin)
            
            # Clientes de exemplo
            cliente1 = Cliente(
                nome='Maria Silva',
                email='maria@email.com',
                telefone='(11) 98888-8888',
                data_nascimento=datetime(1990, 12, 16).date(),
                profissao='Engenheira'
            )
            
            cliente2 = Cliente(
                nome='João Santos',
                email='joao@email.com',
                telefone='(11) 97777-7777',
                data_nascimento=datetime(1985, 12, 17).date(),
                profissao='Professor'
            )
            
            db.session.add(cliente1)
            db.session.add(cliente2)
            db.session.commit()
            
            # Sessões de exemplo
            sessao1 = Sessao(
                cliente_id=1,
                data_hora=datetime.now().replace(hour=9, minute=0, second=0, microsecond=0),
                valor=150.00,
                status='confirmada',
                confirmacao_cliente=True
            )
            
            sessao2 = Sessao(
                cliente_id=2,
                data_hora=datetime.now().replace(hour=14, minute=0, second=0, microsecond=0),
                valor=150.00,
                status='agendada'
            )
            
            db.session.add(sessao1)
            db.session.add(sessao2)
            
            # Pagamentos de exemplo
            pagamento1 = Pagamento(
                cliente_id=1,
                sessao_id=1,
                valor=150.00,
                data_vencimento=datetime.now().date(),
                status='pago',
                data_pagamento=datetime.now().date()
            )
            
            pagamento2 = Pagamento(
                cliente_id=2,
                sessao_id=2,
                valor=150.00,
                data_vencimento=datetime.now().date(),
                status='pendente'
            )
            
            db.session.add(pagamento1)
            db.session.add(pagamento2)
            db.session.commit()

# Inicializar banco quando a aplicação iniciar
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)