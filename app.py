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
app.config['TEMPLATES_AUTO_RELOAD'] = True

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
    # Estatísticas básicas (simuladas por enquanto)
    total_pacientes = 0
    sessoes_hoje = 0
    proximas_sessoes = []
    
    try:
        # Tentar buscar dados reais do banco
        total_pacientes = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).count()
        sessoes_hoje = Sessao.query.filter_by(
            psicologo_id=current_user.id
        ).filter(
            db.func.date(Sessao.data_sessao) == date.today()
        ).count()
        
        proximas_sessoes = Sessao.query.filter_by(
            psicologo_id=current_user.id,
            status='agendada'
        ).filter(
            Sessao.data_sessao >= datetime.now()
        ).order_by(Sessao.data_sessao).limit(5).all()
        
    except Exception as e:
        print(f"Erro ao buscar estatísticas: {e}")
        # Usar valores padrão se houver erro
        pass
    
    return render_template('dashboard.html', 
                         total_pacientes=total_pacientes,
                         sessoes_hoje=sessoes_hoje,
                         proximas_sessoes=proximas_sessoes)

# ========== ROTAS DE PACIENTES ==========

@app.route('/pacientes')
@login_required
def pacientes():
    try:
        # Buscar todos os pacientes do psicólogo logado
        pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id).order_by(Paciente.nome).all()
        
        # Estatísticas
        total_pacientes = len(pacientes_lista)
        pacientes_ativos = len([p for p in pacientes_lista if p.ativo])
        
        # Novos pacientes este mês
        primeiro_dia_mes = date.today().replace(day=1)
        novos_mes = Paciente.query.filter_by(psicologo_id=current_user.id).filter(
            Paciente.data_cadastro >= primeiro_dia_mes
        ).count()
        
        # Sessões este mês (simulado por enquanto)
        try:
            sessoes_mes = Sessao.query.filter_by(psicologo_id=current_user.id).filter(
                db.func.extract('month', Sessao.data_sessao) == date.today().month,
                db.func.extract('year', Sessao.data_sessao) == date.today().year
            ).count()
        except:
            sessoes_mes = 0
        
        return render_template('pacientes.html',
                             pacientes=pacientes_lista,
                             total_pacientes=total_pacientes,
                             pacientes_ativos=pacientes_ativos,
                             novos_mes=novos_mes,
                             sessoes_mes=sessoes_mes,
                             today=date.today())
    
    except Exception as e:
        print(f"Erro na página de pacientes: {e}")
        flash('Erro ao carregar pacientes', 'error')
        return redirect(url_for('dashboard'))

@app.route('/pacientes/novo', methods=['GET', 'POST'])
@login_required
def novo_paciente():
    if request.method == 'POST':
        try:
            # Capturar dados do formulário
            nome = request.form.get('nome', '').strip()
            email = request.form.get('email', '').strip()
            telefone = request.form.get('telefone', '').strip()
            data_nascimento_str = request.form.get('data_nascimento', '')
            endereco = request.form.get('endereco', '').strip()
            observacoes = request.form.get('observacoes', '').strip()
            
            # Validações básicas
            if not nome:
                flash('Nome é obrigatório', 'error')
                return render_template('novo_paciente.html')
            
            # Converter data de nascimento
            data_nascimento = None
            if data_nascimento_str:
                try:
                    data_nascimento = datetime.strptime(data_nascimento_str, '%Y-%m-%d').date()
                except:
                    flash('Data de nascimento inválida', 'error')
                    return render_template('novo_paciente.html')
            
            # Verificar se email já existe (se fornecido)
            if email:
                paciente_existente = Paciente.query.filter_by(email=email, psicologo_id=current_user.id).first()
                if paciente_existente:
                    flash('Já existe um paciente com este email', 'error')
                    return render_template('novo_paciente.html')
            
            # Criar novo paciente
            novo_paciente = Paciente(
                nome=nome,
                email=email if email else None,
                telefone=telefone if telefone else None,
                data_nascimento=data_nascimento,
                endereco=endereco if endereco else None,
                observacoes=observacoes if observacoes else None,
                psicologo_id=current_user.id
            )
            
            db.session.add(novo_paciente)
            db.session.commit()
            
            flash(f'Paciente {nome} cadastrado com sucesso!', 'success')
            return redirect(url_for('pacientes'))
            
        except Exception as e:
            print(f"Erro ao cadastrar paciente: {e}")
            flash('Erro ao cadastrar paciente', 'error')
            db.session.rollback()
    
    return render_template('novo_paciente.html')

@app.route('/pacientes/<int:id>')
@login_required
def ver_paciente(id):
    try:
        paciente = Paciente.query.filter_by(id=id, psicologo_id=current_user.id).first_or_404()
        
        # Buscar sessões do paciente
        sessoes = Sessao.query.filter_by(paciente_id=id).order_by(Sessao.data_sessao.desc()).limit(10).all()
        
        # Buscar evoluções do paciente
        evolucoes = Evolucao.query.filter_by(paciente_id=id).order_by(Evolucao.data_evolucao.desc()).limit(5).all()
        
        return render_template('ver_paciente.html', 
                             paciente=paciente,
                             sessoes=sessoes,
                             evolucoes=evolucoes)
    except Exception as e:
        print(f"Erro ao ver paciente: {e}")
        flash('Paciente não encontrado', 'error')
        return redirect(url_for('pacientes'))

@app.route('/pacientes/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_paciente(id):
    try:
        paciente = Paciente.query.filter_by(id=id, psicologo_id=current_user.id).first_or_404()
        
        if request.method == 'POST':
            # Capturar dados do formulário
            nome = request.form.get('nome', '').strip()
            email = request.form.get('email', '').strip()
            telefone = request.form.get('telefone', '').strip()
            data_nascimento_str = request.form.get('data_nascimento', '')
            endereco = request.form.get('endereco', '').strip()
            observacoes = request.form.get('observacoes', '').strip()
            
            # Validações básicas
            if not nome:
                flash('Nome é obrigatório', 'error')
                return render_template('editar_paciente.html', paciente=paciente)
            
            # Converter data de nascimento
            data_nascimento = None
            if data_nascimento_str:
                try:
                    data_nascimento = datetime.strptime(data_nascimento_str, '%Y-%m-%d').date()
                except:
                    flash('Data de nascimento inválida', 'error')
                    return render_template('editar_paciente.html', paciente=paciente)
            
            # Verificar se email já existe (se fornecido e diferente do atual)
            if email and email != paciente.email:
                paciente_existente = Paciente.query.filter_by(email=email, psicologo_id=current_user.id).first()
                if paciente_existente:
                    flash('Já existe um paciente com este email', 'error')
                    return render_template('editar_paciente.html', paciente=paciente)
            
            # Atualizar dados do paciente
            paciente.nome = nome
            paciente.email = email if email else None
            paciente.telefone = telefone if telefone else None
            paciente.data_nascimento = data_nascimento
            paciente.endereco = endereco if endereco else None
            paciente.observacoes = observacoes if observacoes else None
            
            db.session.commit()
            
            flash(f'Dados de {nome} atualizados com sucesso!', 'success')
            return redirect(url_for('ver_paciente', id=id))
        
        return render_template('editar_paciente.html', paciente=paciente)
        
    except Exception as e:
        print(f"Erro ao editar paciente: {e}")
        flash('Paciente não encontrado', 'error')
        return redirect(url_for('pacientes'))

@app.route('/pacientes/<int:id>/desativar', methods=['POST'])
@login_required
def desativar_paciente(id):
    try:
        paciente = Paciente.query.filter_by(id=id, psicologo_id=current_user.id).first_or_404()
        paciente.ativo = False
        db.session.commit()
        return jsonify({'success': True, 'message': f'Paciente {paciente.nome} desativado com sucesso'})
    except Exception as e:
        print(f"Erro ao desativar paciente: {e}")
        return jsonify({'success': False, 'message': 'Erro ao desativar paciente'})

@app.route('/pacientes/<int:id>/ativar', methods=['POST'])
@login_required
def ativar_paciente(id):
    try:
        paciente = Paciente.query.filter_by(id=id, psicologo_id=current_user.id).first_or_404()
        paciente.ativo = True
        db.session.commit()
        return jsonify({'success': True, 'message': f'Paciente {paciente.nome} ativado com sucesso'})
    except Exception as e:
        print(f"Erro ao ativar paciente: {e}")
        return jsonify({'success': False, 'message': 'Erro ao ativar paciente'})

# ========== FIM DAS ROTAS DE PACIENTES ==========

# Rota de teste para verificar se templates funcionam
@app.route('/teste-template')
@login_required
def teste_template():
    return render_template('dashboard.html', 
                         total_pacientes=5,
                         sessoes_hoje=3,
                         proximas_sessoes=[])

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
