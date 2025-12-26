import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from decimal import Decimal
from sqlalchemy import func, extract
import traceback

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

# ========== MODELOS DO BANCO DE DADOS ==========

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
    
    sessoes = db.relationship('Sessao', backref='paciente', lazy=True)
    evolucoes = db.relationship('Evolucao', backref='paciente', lazy=True)

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
    
    psicologo = db.relationship('Usuario', backref='sessoes_psicologo', lazy=True)

class Evolucao(db.Model):
    __tablename__ = 'evolucoes'
    
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    data_evolucao = db.Column(db.DateTime, default=datetime.utcnow)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(50), default='evolucao')
    humor = db.Column(db.String(20))
    medicamentos = db.Column(db.Text)
    observacoes_privadas = db.Column(db.Text)

class Configuracao(db.Model):
    __tablename__ = 'configuracoes'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, unique=True)
    nome_completo = db.Column(db.String(200))
    crp = db.Column(db.String(20))
    especialidade = db.Column(db.String(200))
    telefone_profissional = db.Column(db.String(20))
    email_profissional = db.Column(db.String(120))
    endereco = db.Column(db.String(300))
    cidade = db.Column(db.String(100))
    estado = db.Column(db.String(2))
    cep = db.Column(db.String(10))
    duracao_sessao = db.Column(db.Integer, default=50)
    valor_sessao = db.Column(db.Numeric(10, 2))
    horario_inicio = db.Column(db.Time)
    horario_fim = db.Column(db.Time)
    dias_atendimento = db.Column(db.String(50))
    lembrete_paciente = db.Column(db.Boolean, default=True)
    antecedencia_lembrete = db.Column(db.Integer, default=24)
    
    usuario = db.relationship('Usuario', backref='configuracao', uselist=False)

# ========== FUNÇÕES AUXILIARES ==========

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

def obter_estatisticas_gerais(data_inicio, data_fim):
    try:
        stats = {}
        stats['total_pacientes'] = Paciente.query.filter_by(psicologo_id=current_user.id).count()
        stats['pacientes_ativos'] = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).count()
        
        sessoes_periodo = Sessao.query.filter(
            Sessao.psicologo_id == current_user.id,
            func.date(Sessao.data_sessao) >= data_inicio,
            func.date(Sessao.data_sessao) <= data_fim
        ).all()
        
        stats['total_sessoes'] = len(sessoes_periodo)
        stats['sessoes_realizadas'] = len([s for s in sessoes_periodo if s.status == 'realizada'])
        stats['sessoes_agendadas'] = len([s for s in sessoes_periodo if s.status == 'agendada'])
        stats['sessoes_canceladas'] = len([s for s in sessoes_periodo if s.status in ['cancelada', 'faltou']])
        stats['receita_total'] = sum(float(s.valor or 0) for s in sessoes_periodo if s.status == 'realizada')
        stats['receita_pendente'] = sum(float(s.valor or 0) for s in sessoes_periodo if s.status == 'agendada')
        
        sessoes_com_valor = [s for s in sessoes_periodo if s.status == 'realizada' and s.valor]
        if sessoes_com_valor:
            stats['valor_medio_sessao'] = stats['receita_total'] / len(sessoes_com_valor)
        else:
            stats['valor_medio_sessao'] = 0
        
        if stats['total_sessoes'] > 0:
            stats['taxa_comparecimento'] = (stats['sessoes_realizadas'] / stats['total_sessoes']) * 100
        else:
            stats['taxa_comparecimento'] = 0
        
        return stats
    except Exception as e:
        print(f"❌ Erro ao obter estatísticas: {e}")
        traceback.print_exc()
        return {}

# ========== ROTAS PRINCIPAIS ==========

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
    print("✅ Rota /dashboard acessada")
    total_pacientes = 0
    sessoes_hoje = 0
    proximas_sessoes = []
    sessoes_mes = 0
    receita_mes = 0
    
    try:
        total_pacientes = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).count()
        hoje = date.today()
        sessoes_hoje = Sessao.query.filter_by(psicologo_id=current_user.id).filter(
            db.func.date(Sessao.data_sessao) == hoje
        ).count()
        
        proximas_sessoes = Sessao.query.filter_by(
            psicologo_id=current_user.id,
            status='agendada'
        ).filter(
            Sessao.data_sessao >= datetime.now(),
            Sessao.data_sessao <= datetime.now() + timedelta(days=7)
        ).order_by(Sessao.data_sessao).limit(5).all()
        
        primeiro_dia_mes = hoje.replace(day=1)
        sessoes_mes = Sessao.query.filter_by(psicologo_id=current_user.id).filter(
            db.func.date(Sessao.data_sessao) >= primeiro_dia_mes,
            Sessao.status.in_(['realizada', 'agendada'])
        ).count()
        
        receita_query = db.session.query(db.func.sum(Sessao.valor)).filter_by(
            psicologo_id=current_user.id,
            status='realizada'
        ).filter(
            db.func.date(Sessao.data_sessao) >= primeiro_dia_mes
        ).scalar()
        receita_mes = float(receita_query) if receita_query else 0
    except Exception as e:
        print(f"❌ Erro ao buscar estatísticas do dashboard: {e}")
        traceback.print_exc()
    
    return render_template('dashboard.html', 
                         total_pacientes=total_pacientes,
                         sessoes_hoje=sessoes_hoje,
                         proximas_sessoes=proximas_sessoes,
                         sessoes_mes=sessoes_mes,
                         receita_mes=receita_mes)

# ========== ROTAS DE PACIENTES ==========

@app.route('/pacientes')
@login_required
def pacientes():
    print("✅ Rota /pacientes acessada")
    try:
        search = request.args.get('search', '')
        
        if search:
            pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id).filter(
                db.or_(
                    Paciente.nome.ilike(f'%{search}%'),
                    Paciente.email.ilike(f'%{search}%'),
                    Paciente.telefone.ilike(f'%{search}%')
                )
            ).order_by(Paciente.nome).all()
        else:
            pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id).order_by(Paciente.nome).all()
        
        total_pacientes = Paciente.query.filter_by(psicologo_id=current_user.id).count()
        pacientes_ativos = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).count()
        primeiro_dia_mes = date.today().replace(day=1)
        novos_mes = Paciente.query.filter_by(psicologo_id=current_user.id).filter(
            Paciente.data_cadastro >= primeiro_dia_mes
        ).count()
        
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
        print(f"❌ Erro na página de pacientes: {e}")
        traceback.print_exc()
        flash('Erro ao carregar pacientes', 'error')
        return redirect(url_for('dashboard'))

@app.route('/pacientes/novo', methods=['GET', 'POST'])
@login_required
def novo_paciente():
    if request.method == 'POST':
        try:
            nome = request.form.get('nome', '').strip()
            email = request.form.get('email', '').strip()
            telefone = request.form.get('telefone', '').strip()
            data_nascimento_str = request.form.get('data_nascimento', '')
            endereco = request.form.get('endereco', '').strip()
            observacoes = request.form.get('observacoes', '').strip()
            
            if not nome:
                flash('Nome é obrigatório', 'error')
                return render_template('novo_paciente.html')
            
            data_nascimento = None
            if data_nascimento_str:
                try:
                    data_nascimento = datetime.strptime(data_nascimento_str, '%Y-%m-%d').date()
                except:
                    flash('Data de nascimento inválida', 'error')
                    return render_template('novo_paciente.html')
            
            if email:
                paciente_existente = Paciente.query.filter_by(email=email, psicologo_id=current_user.id).first()
                if paciente_existente:
                    flash('Já existe um paciente com este email', 'error')
                    return render_template('novo_paciente.html')
            
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
            print(f"❌ Erro ao cadastrar paciente: {e}")
            traceback.print_exc()
            flash('Erro ao cadastrar paciente', 'error')
            db.session.rollback()
    
    return render_template('novo_paciente.html')

@app.route('/pacientes/<int:id>')
@login_required
def ver_paciente(id):
    try:
        paciente = Paciente.query.filter_by(id=id, psicologo_id=current_user.id).first_or_404()
        sessoes = Sessao.query.filter_by(paciente_id=id).order_by(Sessao.data_sessao.desc()).limit(10).all()
        evolucoes = Evolucao.query.filter_by(paciente_id=id).order_by(Evolucao.data_evolucao.desc()).limit(5).all()
        
        return render_template('ver_paciente.html', 
                             paciente=paciente,
                             sessoes=sessoes,
                             evolucoes=evolucoes,
                             today=date.today())
    except Exception as e:
        print(f"❌ Erro ao ver paciente: {e}")
        traceback.print_exc()
        flash('Paciente não encontrado', 'error')
        return redirect(url_for('pacientes'))

@app.route('/pacientes/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_paciente(id):
    try:
        paciente = Paciente.query.filter_by(id=id, psicologo_id=current_user.id).first_or_404()
        
        if request.method == 'POST':
            nome = request.form.get('nome', '').strip()
            email = request.form.get('email', '').strip()
            telefone = request.form.get('telefone', '').strip()
            data_nascimento_str = request.form.get('data_nascimento', '')
            endereco = request.form.get('endereco', '').strip()
            observacoes = request.form.get('observacoes', '').strip()
            
            if not nome:
                flash('Nome é obrigatório', 'error')
                return render_template('editar_paciente.html', paciente=paciente, today=date.today())
            
            data_nascimento = None
            if data_nascimento_str:
                try:
                    data_nascimento = datetime.strptime(data_nascimento_str, '%Y-%m-%d').date()
                except:
                    flash('Data de nascimento inválida', 'error')
                    return render_template('editar_paciente.html', paciente=paciente, today=date.today())
            
            if email and email != paciente.email:
                paciente_existente = Paciente.query.filter_by(email=email, psicologo_id=current_user.id).first()
                if paciente_existente:
                    flash('Já existe um paciente com este email', 'error')
                    return render_template('editar_paciente.html', paciente=paciente, today=date.today())
            
            paciente.nome = nome
            paciente.email = email if email else None
            paciente.telefone = telefone if telefone else None
            paciente.data_nascimento = data_nascimento
            paciente.endereco = endereco if endereco else None
            paciente.observacoes = observacoes if observacoes else None
            
            db.session.commit()
            
            flash(f'Dados de {nome} atualizados com sucesso!', 'success')
            return redirect(url_for('ver_paciente', id=id))
        
        return render_template('editar_paciente.html', paciente=paciente, today=date.today())
    except Exception as e:
        print(f"❌ Erro ao editar paciente: {e}")
        traceback.print_exc()
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
        print(f"❌ Erro ao desativar paciente: {e}")
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
        print(f"❌ Erro ao ativar paciente: {e}")
        return jsonify({'success': False, 'message': 'Erro ao ativar paciente'})

# ========== ROTAS DE SESSÕES ==========

@app.route('/sessoes')
@login_required
def sessoes():
    print("✅ Rota /sessoes acessada")
    try:
        status_filter = request.args.get('status', '')
        paciente_filter = request.args.get('paciente', '')
        data_inicio = request.args.get('data_inicio', '')
        data_fim = request.args.get('data_fim', '')
        
        query = Sessao.query.filter_by(psicologo_id=current_user.id)
        
        if status_filter:
            query = query.filter(Sessao.status == status_filter)
        
        if paciente_filter:
            query = query.filter(Sessao.paciente_id == paciente_filter)
        
        if data_inicio:
            try:
                data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                query = query.filter(db.func.date(Sessao.data_sessao) >= data_inicio_obj)
            except:
                pass
        
        if data_fim:
            try:
                data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
                query = query.filter(db.func.date(Sessao.data_sessao) <= data_fim_obj)
            except:
                pass
        
        sessoes_lista = query.order_by(Sessao.data_sessao.desc()).all()
        pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).order_by(Paciente.nome).all()
        
        total_sessoes = Sessao.query.filter_by(psicologo_id=current_user.id).count()
        sessoes_agendadas = Sessao.query.filter_by(psicologo_id=current_user.id, status='agendada').count()
        sessoes_realizadas = Sessao.query.filter_by(psicologo_id=current_user.id, status='realizada').count()
        
        receita_query = db.session.query(db.func.sum(Sessao.valor)).filter_by(
            psicologo_id=current_user.id,
            status='realizada'
        ).scalar()
        receita_total = float(receita_query) if receita_query else 0
        
        return render_template('sessoes.html',
                             sessoes=sessoes_lista,
                             pacientes=pacientes_lista,
                             total_sessoes=total_sessoes,
                             sessoes_agendadas=sessoes_agendadas,
                             sessoes_realizadas=sessoes_realizadas,
                             receita_total=receita_total,
                             today=date.today())
    except Exception as e:
        print(f"❌ Erro na página de sessões: {e}")
        traceback.print_exc()
        flash('Erro ao carregar sessões', 'error')
        return redirect(url_for('dashboard'))

@app.route('/sessoes/nova', methods=['GET', 'POST'])
@login_required
def nova_sessao():
    if request.method == 'POST':
        try:
            paciente_id = request.form.get('paciente_id')
            data_sessao_str = request.form.get('data_sessao')
            hora_sessao = request.form.get('hora_sessao')
            duracao = request.form.get('duracao', 50)
            valor_str = request.form.get('valor', '').strip()
            observacoes = request.form.get('observacoes', '').strip()
            
            if not paciente_id or paciente_id == '' or paciente_id == 'None':
                flash('Paciente é obrigatório', 'error')
                pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).order_by(Paciente.nome).all()
                return render_template('nova_sessao.html', pacientes=pacientes_lista)
            
            try:
                paciente_id_int = int(paciente_id)
            except (ValueError, TypeError):
                flash('Paciente inválido', 'error')
                pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).order_by(Paciente.nome).all()
                return render_template('nova_sessao.html', pacientes=pacientes_lista)
            
            if not data_sessao_str or not hora_sessao:
                flash('Data e hora são obrigatórios', 'error')
                pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).order_by(Paciente.nome).all()
                return render_template('nova_sessao.html', pacientes=pacientes_lista)
            
            try:
                data_sessao = datetime.strptime(f"{data_sessao_str} {hora_sessao}", '%Y-%m-%d %H:%M')
            except Exception:
                flash('Data ou hora inválida', 'error')
                pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).order_by(Paciente.nome).all()
                return render_template('nova_sessao.html', pacientes=pacientes_lista)
            
            if data_sessao < datetime.now():
                flash('Não é possível agendar sessão no passado', 'error')
                pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).order_by(Paciente.nome).all()
                return render_template('nova_sessao.html', pacientes=pacientes_lista)
            
            paciente = Paciente.query.filter_by(id=paciente_id_int, psicologo_id=current_user.id).first()
            if not paciente:
                flash('Paciente não encontrado', 'error')
                pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).order_by(Paciente.nome).all()
                return render_template('nova_sessao.html', pacientes=pacientes_lista)
            
            conflito = Sessao.query.filter(
                Sessao.psicologo_id == current_user.id,
                Sessao.status == 'agendada',
                Sessao.data_sessao == data_sessao
            ).first()
            
            if conflito:
                flash('Já existe uma sessão agendada para este horário', 'error')
                pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).order_by(Paciente.nome).all()
                return render_template('nova_sessao.html', pacientes=pacientes_lista)
            
            valor = None
            if valor_str and valor_str.strip():
                try:
                    valor_limpo = valor_str.replace(',', '.').strip()
                    valor = Decimal(valor_limpo)
                except Exception:
                    flash('Valor inválido', 'error')
                    pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).order_by(Paciente.nome).all()
                    return render_template('nova_sessao.html', pacientes=pacientes_lista)
            
            nova_sessao_obj = Sessao(
                paciente_id=paciente_id_int,
                psicologo_id=current_user.id,
                data_sessao=data_sessao,
                duracao=int(duracao),
                valor=valor,
                observacoes=observacoes if observacoes else None
            )
            
            db.session.add(nova_sessao_obj)
            db.session.commit()
            
            flash(f'Sessão agendada com {paciente.nome} para {data_sessao.strftime("%d/%m/%Y às %H:%M")}!', 'success')
            return redirect(url_for('sessoes'))
        except Exception as e:
            print(f"❌ Erro ao salvar sessão: {e}")
            traceback.print_exc()
            flash('Erro ao salvar sessão no banco de dados', 'error')
            db.session.rollback()
    
    try:
        pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).order_by(Paciente.nome).all()
    except Exception:
        pacientes_lista = []
    
    return render_template('nova_sessao.html', pacientes=pacientes_lista)

@app.route('/sessoes/<int:id>')
@login_required
def ver_sessao(id):
    try:
        sessao = Sessao.query.filter_by(id=id, psicologo_id=current_user.id).first_or_404()
        return render_template('ver_sessao.html', sessao=sessao, today=date.today())
    except Exception as e:
        print(f"❌ Erro ao ver sessão: {e}")
        flash('Sessão não encontrada', 'error')
        return redirect(url_for('sessoes'))

@app.route('/sessoes/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_sessao(id):
    try:
        sessao = Sessao.query.filter_by(id=id, psicologo_id=current_user.id).first_or_404()
        
        if request.method == 'POST':
            data_sessao_str = request.form.get('data_sessao')
            hora_sessao = request.form.get('hora_sessao')
            duracao = request.form.get('duracao', 50)
            valor_str = request.form.get('valor', '').strip()
            observacoes = request.form.get('observacoes', '').strip()
            
            if not data_sessao_str or not hora_sessao:
                flash('Data e hora são obrigatórios', 'error')
                return render_template('editar_sessao.html', sessao=sessao, today=date.today())
            
            try:
                data_sessao = datetime.strptime(f"{data_sessao_str} {hora_sessao}", '%Y-%m-%d %H:%M')
            except:
                flash('Data ou hora inválida', 'error')
                return render_template('editar_sessao.html', sessao=sessao, today=date.today())
            
            conflito = Sessao.query.filter(
                Sessao.psicologo_id == current_user.id,
                Sessao.status == 'agendada',
                Sessao.data_sessao == data_sessao,
                Sessao.id != id
            ).first()
            
            if conflito:
                flash('Já existe uma sessão agendada para este horário', 'error')
                return render_template('editar_sessao.html', sessao=sessao, today=date.today())
            
            valor = None
            if valor_str and valor_str.strip():
                try:
                    valor = Decimal(valor_str.replace(',', '.'))
                except:
                    flash('Valor inválido', 'error')
                    return render_template('editar_sessao.html', sessao=sessao, today=date.today())
            
            sessao.data_sessao = data_sessao
            sessao.duracao = int(duracao)
            sessao.valor = valor
            sessao.observacoes = observacoes if observacoes else None
            
            db.session.commit()
            
            flash('Sessão atualizada com sucesso!', 'success')
            return redirect(url_for('ver_sessao', id=id))
        
        return render_template('editar_sessao.html', sessao=sessao, today=date.today())
    except Exception as e:
        print(f"❌ Erro ao editar sessão: {e}")
        flash('Sessão não encontrada', 'error')
        return redirect(url_for('sessoes'))

@app.route('/sessoes/<int:id>/marcar-realizada', methods=['POST'])
@login_required
def marcar_sessao_realizada(id):
    try:
        sessao = Sessao.query.filter_by(id=id, psicologo_id=current_user.id).first_or_404()
        sessao.status = 'realizada'
        db.session.commit()
        return jsonify({'success': True, 'message': 'Sessão marcada como realizada'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Erro ao atualizar sessão'})

@app.route('/sessoes/<int:id>/marcar-faltou', methods=['POST'])
@login_required
def marcar_sessao_faltou(id):
    try:
        sessao = Sessao.query.filter_by(id=id, psicologo_id=current_user.id).first_or_404()
        sessao.status = 'faltou'
        db.session.commit()
        return jsonify({'success': True, 'message': 'Sessão marcada como falta'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Erro ao atualizar sessão'})

@app.route('/sessoes/<int:id>/cancelar', methods=['POST'])
@login_required
def cancelar_sessao(id):
    try:
        sessao = Sessao.query.filter_by(id=id, psicologo_id=current_user.id).first_or_404()
        sessao.status = 'cancelada'
        db.session.commit()
        return jsonify({'success': True, 'message': 'Sessão cancelada'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Erro ao cancelar sessão'})

@app.route('/sessoes/<int:id>/reagendar', methods=['POST'])
@login_required
def reagendar_sessao(id):
    try:
        sessao = Sessao.query.filter_by(id=id, psicologo_id=current_user.id).first_or_404()
        sessao.status = 'agendada'
        db.session.commit()
        return jsonify({'success': True, 'message': 'Sessão reagendada'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Erro ao reagendar sessão'})

# ========== ROTAS DE PRONTUÁRIO/EVOLUÇÃO ==========

@app.route('/prontuario/<int:paciente_id>')
@login_required
def prontuario(paciente_id):
    print("✅ Rota /prontuario acessada")
    try:
        paciente = Paciente.query.filter_by(id=paciente_id, psicologo_id=current_user.id).first_or_404()
        evolucoes = Evolucao.query.filter_by(paciente_id=paciente_id).order_by(Evolucao.data_evolucao.desc()).all()
        return render_template('prontuario.html', paciente=paciente, evolucoes=evolucoes, today=date.today())
    except Exception as e:
        print(f"❌ Erro ao ver prontuário: {e}")
        traceback.print_exc()
        flash('Paciente não encontrado', 'error')
        return redirect(url_for('pacientes'))

@app.route('/prontuario/<int:paciente_id>/nova', methods=['POST'])
@login_required
def nova_evolucao_prontuario(paciente_id):
    try:
        paciente = Paciente.query.filter_by(id=paciente_id, psicologo_id=current_user.id).first_or_404()
        
        tipo = request.form.get('tipo', 'evolucao')
        titulo = request.form.get('titulo', '').strip()
        conteudo = request.form.get('conteudo', '').strip()
        humor = request.form.get('humor', '')
        medicamentos = request.form.get('medicamentos', '').strip()
        observacoes_privadas = request.form.get('observacoes_privadas', '').strip()
        
        if not titulo or not conteudo:
            flash('Título e conteúdo são obrigatórios', 'error')
            return redirect(url_for('prontuario', paciente_id=paciente_id))
        
        nova_evolucao = Evolucao(
            paciente_id=paciente_id,
            tipo=tipo,
            titulo=titulo,
            descricao=conteudo,
            humor=humor if humor else None,
            medicamentos=medicamentos if medicamentos else None,
            observacoes_privadas=observacoes_privadas if observacoes_privadas else None
        )
        
        db.session.add(nova_evolucao)
        db.session.commit()
        
        flash('Evolução registrada com sucesso!', 'success')
        return redirect(url_for('prontuario', paciente_id=paciente_id))
    except Exception as e:
        print(f"❌ Erro ao criar evolução: {e}")
        traceback.print_exc()
        flash('Erro ao registrar evolução', 'error')
        db.session.rollback()
        return redirect(url_for('prontuario', paciente_id=paciente_id))

@app.route('/evolucoes')
@login_required
def evolucoes():
    print("✅ Rota /evolucoes acessada")
    try:
        paciente_filter = request.args.get('paciente', '')
        data_inicio = request.args.get('data_inicio', '')
        data_fim = request.args.get('data_fim', '')
        
        query = Evolucao.query.join(Paciente).filter(Paciente.psicologo_id == current_user.id)
        
        if paciente_filter:
            query = query.filter(Evolucao.paciente_id == paciente_filter)
        
        if data_inicio:
            try:
                data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                query = query.filter(func.date(Evolucao.data_evolucao) >= data_inicio_obj)
            except:
                pass
        
        if data_fim:
            try:
                data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
                query = query.filter(func.date(Evolucao.data_evolucao) <= data_fim_obj)
            except:
                pass
        
        evolucoes_lista = query.order_by(Evolucao.data_evolucao.desc()).all()
        pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).order_by(Paciente.nome).all()
        
        total_evolucoes = Evolucao.query.join(Paciente).filter(Paciente.psicologo_id == current_user.id).count()
        
        primeiro_dia_mes = date.today().replace(day=1)
        evolucoes_mes = Evolucao.query.join(Paciente).filter(
            Paciente.psicologo_id == current_user.id,
            func.date(Evolucao.data_evolucao) >= primeiro_dia_mes
        ).count()
        
        return render_template('evolucoes.html',
                             evolucoes=evolucoes_lista,
                             pacientes=pacientes_lista,
                             total_evolucoes=total_evolucoes,
                             evolucoes_mes=evolucoes_mes,
                             today=date.today())
    except Exception as e:
        print(f"❌ Erro na página de evoluções: {e}")
        traceback.print_exc()
        flash('Erro ao carregar evoluções', 'error')
        return redirect(url_for('dashboard'))

@app.route('/evolucoes/nova', methods=['GET', 'POST'])
@login_required
def nova_evolucao():
    if request.method == 'POST':
        try:
            paciente_id = request.form.get('paciente_id')
            titulo = request.form.get('titulo', '').strip()
            descricao = request.form.get('descricao', '').strip()
            tipo = request.form.get('tipo', 'evolucao')
            
            if not paciente_id or paciente_id == '' or paciente_id == 'None':
                flash('Paciente é obrigatório', 'error')
                pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).order_by(Paciente.nome).all()
                return render_template('nova_evolucao.html', pacientes=pacientes_lista)
            
            if not titulo:
                flash('Título é obrigatório', 'error')
                pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).order_by(Paciente.nome).all()
                return render_template('nova_evolucao.html', pacientes=pacientes_lista)
            
            if not descricao:
                flash('Descrição é obrigatória', 'error')
                pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).order_by(Paciente.nome).all()
                return render_template('nova_evolucao.html', pacientes=pacientes_lista)
            
            paciente = Paciente.query.filter_by(id=int(paciente_id), psicologo_id=current_user.id).first()
            if not paciente:
                flash('Paciente não encontrado', 'error')
                pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).order_by(Paciente.nome).all()
                return render_template('nova_evolucao.html', pacientes=pacientes_lista)
            
            nova_evolucao_obj = Evolucao(
                paciente_id=int(paciente_id),
                titulo=titulo,
                descricao=descricao,
                tipo=tipo
            )
            
            db.session.add(nova_evolucao_obj)
            db.session.commit()
            
            flash(f'Evolução de {paciente.nome} registrada com sucesso!', 'success')
            return redirect(url_for('evolucoes'))
        except Exception as e:
            print(f"❌ Erro ao criar evolução: {e}")
            traceback.print_exc()
            flash('Erro ao registrar evolução', 'error')
            db.session.rollback()
    
    try:
        pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).order_by(Paciente.nome).all()
    except Exception:
        pacientes_lista = []
    
    return render_template('nova_evolucao.html', pacientes=pacientes_lista)

@app.route('/evolucoes/<int:id>')
@login_required
def ver_evolucao(id):
    try:
        evolucao = Evolucao.query.join(Paciente).filter(
            Evolucao.id == id,
            Paciente.psicologo_id == current_user.id
        ).first_or_404()
        
        return render_template('ver_evolucao.html', evolucao=evolucao, today=date.today())
    except Exception as e:
        print(f"❌ Erro ao ver evolução: {e}")
        flash('Evolução não encontrada', 'error')
        return redirect(url_for('evolucoes'))

@app.route('/evolucoes/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_evolucao(id):
    try:
        evolucao = Evolucao.query.join(Paciente).filter(
            Evolucao.id == id,
            Paciente.psicologo_id == current_user.id
        ).first_or_404()
        
        if request.method == 'POST':
            titulo = request.form.get('titulo', '').strip()
            descricao = request.form.get('descricao', '').strip()
            tipo = request.form.get('tipo', 'evolucao')
            
            if not titulo:
                flash('Título é obrigatório', 'error')
                return render_template('editar_evolucao.html', evolucao=evolucao, today=date.today())
            
            if not descricao:
                flash('Descrição é obrigatória', 'error')
                return render_template('editar_evolucao.html', evolucao=evolucao, today=date.today())
            
            evolucao.titulo = titulo
            evolucao.descricao = descricao
            evolucao.tipo = tipo
            
            db.session.commit()
            
            flash('Evolução atualizada com sucesso!', 'success')
            return redirect(url_for('ver_evolucao', id=id))
        
        return render_template('editar_evolucao.html', evolucao=evolucao, today=date.today())
    except Exception as e:
        print(f"❌ Erro ao editar evolução: {e}")
        flash('Evolução não encontrada', 'error')
        return redirect(url_for('evolucoes'))

@app.route('/evolucoes/<int:id>/excluir', methods=['POST'])
@login_required
def excluir_evolucao(id):
    try:
        evolucao = Evolucao.query.join(Paciente).filter(
            Evolucao.id == id,
            Paciente.psicologo_id == current_user.id
        ).first_or_404()
        
        db.session.delete(evolucao)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Evolução excluída com sucesso'})
    except Exception as e:
        return jsonify({'success': False, 'message': 'Erro ao excluir evolução'})

# ========== ROTAS DE CONFIGURAÇÕES ==========

@app.route('/configuracoes')
@login_required
def configuracoes():
    print("✅ Rota /configuracoes acessada")
    try:
        config = Configuracao.query.filter_by(usuario_id=current_user.id).first()
        return render_template('configuracoes.html', config=config, usuario=current_user, today=date.today())
    except Exception as e:
        print(f"❌ Erro ao carregar configurações: {e}")
        traceback.print_exc()
        return render_template('configuracoes.html', config=None, usuario=current_user, today=date.today())

@app.route('/configuracoes/salvar', methods=['POST'])
@login_required
def salvar_configuracoes():
    try:
        config = Configuracao.query.filter_by(usuario_id=current_user.id).first()
        
        if not config:
            config = Configuracao(usuario_id=current_user.id)
            db.session.add(config)
        
        config.nome_completo = request.form.get('nome_completo')
        config.crp = request.form.get('crp')
        config.especialidade = request.form.get('especialidade')
        config.telefone_profissional = request.form.get('telefone_profissional')
        config.email_profissional = request.form.get('email_profissional')
        config.endereco = request.form.get('endereco')
        config.cidade = request.form.get('cidade')
        config.estado = request.form.get('estado')
        config.cep = request.form.get('cep')
        
        duracao = request.form.get('duracao_sessao')
        if duracao:
            config.duracao_sessao = int(duracao)
        
        valor = request.form.get('valor_sessao')
        if valor:
            try:
                config.valor_sessao = Decimal(valor.replace(',', '.'))
            except:
                pass
        
        horario_inicio = request.form.get('horario_inicio')
        horario_fim = request.form.get('horario_fim')
        if horario_inicio:
            try:
                config.horario_inicio = datetime.strptime(horario_inicio, '%H:%M').time()
            except:
                pass
        if horario_fim:
            try:
                config.horario_fim = datetime.strptime(horario_fim, '%H:%M').time()
            except:
                pass
        
        dias = request.form.getlist('dias_atendimento')
        config.dias_atendimento = ','.join(dias) if dias else None
        config.lembrete_paciente = 'lembrete_paciente' in request.form
        
        antecedencia = request.form.get('antecedencia_lembrete')
        if antecedencia:
            config.antecedencia_lembrete = int(antecedencia)
        
        senha_atual = request.form.get('senha_atual')
        nova_senha = request.form.get('nova_senha')
        confirmar_senha = request.form.get('confirmar_senha')
        
        if senha_atual and nova_senha:
            if current_user.check_password(senha_atual):
                if nova_senha == confirmar_senha:
                    if len(nova_senha) >= 6:
                        current_user.set_password(nova_senha)
                        flash('Senha alterada com sucesso!', 'success')
                    else:
                        flash('A nova senha deve ter pelo menos 6 caracteres!', 'warning')
                else:
                    flash('As senhas não coincidem!', 'danger')
                    return redirect(url_for('configuracoes'))
            else:
                flash('Senha atual incorreta!', 'danger')
                return redirect(url_for('configuracoes'))
        
        db.session.commit()
        flash('Configurações salvas com sucesso!', 'success')
        return redirect(url_for('configuracoes'))
    except Exception as e:
        print(f"❌ Erro ao salvar configurações: {e}")
        traceback.print_exc()
        flash('Erro ao salvar configurações', 'error')
        db.session.rollback()
        return redirect(url_for('configuracoes'))

@app.route('/configuracoes/perfil', methods=['GET', 'POST'])
@login_required
def configuracoes_perfil():
    if request.method == 'POST':
        try:
            nome = request.form.get('nome', '').strip()
            email = request.form.get('email', '').strip()
            
            if not nome:
                flash('Nome é obrigatório', 'error')
                return render_template('configuracoes_perfil.html', usuario=current_user, today=date.today())
            
            if not email:
                flash('Email é obrigatório', 'error')
                return render_template('configuracoes_perfil.html', usuario=current_user, today=date.today())
            
            if email != current_user.email:
                usuario_existente = Usuario.query.filter_by(email=email).first()
                if usuario_existente:
                    flash('Este email já está sendo usado por outro usuário', 'error')
                    return render_template('configuracoes_perfil.html', usuario=current_user, today=date.today())
            
            current_user.nome = nome
            current_user.email = email
            db.session.commit()
            
            flash('Perfil atualizado com sucesso!', 'success')
            return redirect(url_for('configuracoes'))
        except Exception as e:
            print(f"❌ Erro ao atualizar perfil: {e}")
            flash('Erro ao atualizar perfil', 'error')
            db.session.rollback()
    
    return render_template('configuracoes_perfil.html', usuario=current_user, today=date.today())

@app.route('/configuracoes/senha', methods=['GET', 'POST'])
@login_required
def configuracoes_senha():
    if request.method == 'POST':
        try:
            senha_atual = request.form.get('senha_atual', '')
            nova_senha = request.form.get('nova_senha', '')
            confirmar_senha = request.form.get('confirmar_senha', '')
            
            if not senha_atual:
                flash('Senha atual é obrigatória', 'error')
                return render_template('configuracoes_senha.html', today=date.today())
            
            if not nova_senha:
                flash('Nova senha é obrigatória', 'error')
                return render_template('configuracoes_senha.html', today=date.today())
            
            if len(nova_senha) < 6:
                flash('Nova senha deve ter pelo menos 6 caracteres', 'error')
                return render_template('configuracoes_senha.html', today=date.today())
            
            if nova_senha != confirmar_senha:
                flash('Confirmação de senha não confere', 'error')
                return render_template('configuracoes_senha.html', today=date.today())
            
            if not current_user.check_password(senha_atual):
                flash('Senha atual incorreta', 'error')
                return render_template('configuracoes_senha.html', today=date.today())
            
            current_user.set_password(nova_senha)
            db.session.commit()
            
            flash('Senha alterada com sucesso!', 'success')
            return redirect(url_for('configuracoes'))
        except Exception as e:
            print(f"❌ Erro ao alterar senha: {e}")
            flash('Erro ao alterar senha', 'error')
            db.session.rollback()
    
    return render_template('configuracoes_senha.html', today=date.today())

# ========== ROTAS DE RELATÓRIOS ==========

@app.route('/relatorios')
@login_required
def relatorios():
    print("✅ Rota /relatorios acessada")
    try:
        periodo = request.args.get('periodo', '12')
        hoje = date.today()
        
        if periodo == '1':
            data_inicio = hoje.replace(day=1)
        elif periodo == '3':
            data_inicio = hoje - timedelta(days=90)
        elif periodo == '6':
            data_inicio = hoje - timedelta(days=180)
        else:
            data_inicio = hoje - timedelta(days=365)
        
        stats = obter_estatisticas_gerais(data_inicio, hoje)
        
        return render_template('relatorios.html', 
                             stats=stats,
                             periodo=periodo,
                             data_inicio=data_inicio.strftime('%Y-%m-%d'),
                             data_fim=hoje.strftime('%Y-%m-%d'))
    except Exception as e:
        print(f"❌ Erro na página de relatórios: {e}")
        traceback.print_exc()
        flash('Erro ao carregar relatórios', 'error')
        return redirect(url_for('dashboard'))

@app.route('/relatorios/financeiro')
@login_required
def relatorio_financeiro():
    try:
        data_inicio = request.args.get('data_inicio', '')
        data_fim = request.args.get('data_fim', '')
        
        if not data_inicio or not data_fim:
            hoje = date.today()
            data_fim = hoje.strftime('%Y-%m-%d')
            data_inicio = hoje.replace(day=1).strftime('%Y-%m-%d')
        
        data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
        
        sessoes = Sessao.query.filter(
            Sessao.psicologo_id == current_user.id,
            func.date(Sessao.data_sessao) >= data_inicio_obj,
            func.date(Sessao.data_sessao) <= data_fim_obj
        ).order_by(Sessao.data_sessao.desc()).all()
        
        total_receita = sum(float(s.valor or 0) for s in sessoes if s.status == 'realizada')
        total_sessoes = len([s for s in sessoes if s.status == 'realizada'])
        receita_pendente = sum(float(s.valor or 0) for s in sessoes if s.status == 'agendada')
        sessoes_canceladas = len([s for s in sessoes if s.status in ['cancelada', 'faltou']])
        
        receita_mensal = {}
        for sessao in sessoes:
            if sessao.status == 'realizada' and sessao.valor:
                mes_ano = sessao.data_sessao.strftime('%m/%Y')
                if mes_ano not in receita_mensal:
                    receita_mensal[mes_ano] = 0
                receita_mensal[mes_ano] += float(sessao.valor)
        
        return render_template('relatorio_financeiro.html',
                             sessoes=sessoes,
                             total_receita=total_receita,
                             total_sessoes=total_sessoes,
                             receita_pendente=receita_pendente,
                             sessoes_canceladas=sessoes_canceladas,
                             receita_mensal=receita_mensal,
                             data_inicio=data_inicio,
                             data_fim=data_fim)
    except Exception as e:
        print(f"❌ Erro no relatório financeiro: {e}")
        traceback.print_exc()
        flash('Erro ao gerar relatório financeiro', 'error')
        return redirect(url_for('relatorios'))

# ========== APIs PARA GRÁFICOS ==========

@app.route('/api/relatorios/receita-mensal')
@login_required
def api_receita_mensal():
    try:
        periodo = int(request.args.get('periodo', 12))
        hoje = date.today()
        meses = []
        receitas = []
        
        for i in range(periodo):
            mes_atual = hoje.replace(day=1) - timedelta(days=i*30)
            primeiro_dia = mes_atual.replace(day=1)
            
            if mes_atual.month == 12:
                ultimo_dia = mes_atual.replace(year=mes_atual.year+1, month=1, day=1) - timedelta(days=1)
            else:
                ultimo_dia = mes_atual.replace(month=mes_atual.month+1, day=1) - timedelta(days=1)
            
            receita = db.session.query(func.sum(Sessao.valor)).filter(
                Sessao.psicologo_id == current_user.id,
                Sessao.status == 'realizada',
                func.date(Sessao.data_sessao) >= primeiro_dia,
                func.date(Sessao.data_sessao) <= ultimo_dia
            ).scalar() or 0
            
            meses.insert(0, mes_atual.strftime('%m/%Y'))
            receitas.insert(0, float(receita))
        
        return jsonify({'labels': meses, 'data': receitas})
    except Exception as e:
        print(f"❌ Erro na API receita mensal: {e}")
        return jsonify({'error': 'Erro ao buscar dados'}), 500

@app.route('/api/relatorios/sessoes-status')
@login_required
def api_sessoes_status():
    try:
        periodo = int(request.args.get('periodo', 12))
        hoje = date.today()
        data_inicio = hoje - timedelta(days=periodo*30)
        
        status_counts = db.session.query(
            Sessao.status,
            func.count(Sessao.id)
        ).filter(
            Sessao.psicologo_id == current_user.id,
            func.date(Sessao.data_sessao) >= data_inicio
        ).group_by(Sessao.status).all()
        
        labels = []
        data = []
        colors = {
            'realizada': '#28a745',
            'agendada': '#007bff',
            'cancelada': '#dc3545',
            'faltou': '#ffc107'
        }
        background_colors = []
        
        for status, count in status_counts:
            labels.append(status.title())
            data.append(count)
            background_colors.append(colors.get(status, '#6c757d'))
        
        return jsonify({'labels': labels, 'data': data, 'backgroundColor': background_colors})
    except Exception as e:
        print(f"❌ Erro na API sessões status: {e}")
        return jsonify({'error': 'Erro ao buscar dados'}), 500

@app.route('/api/relatorios/pacientes-ativos')
@login_required
def api_pacientes_ativos():
    try:
        ativos = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).count()
        inativos = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=False).count()
        
        return jsonify({
            'labels': ['Ativos', 'Inativos'],
            'data': [ativos, inativos],
            'backgroundColor': ['#28a745', '#dc3545']
        })
    except Exception as e:
        print(f"❌ Erro na API pacientes ativos: {e}")
        return jsonify({'error': 'Erro ao buscar dados'}), 500

@app.route('/api/relatorios/evolucao-sessoes')
@login_required
def api_evolucao_sessoes():
    try:
        periodo = int(request.args.get('periodo', 12))
        hoje = date.today()
        semanas = []
        sessoes_realizadas = []
        sessoes_agendadas = []
        
        for i in range(periodo):
            inicio_semana = hoje - timedelta(days=hoje.weekday() + i*7)
            fim_semana = inicio_semana + timedelta(days=6)
            
            realizadas = Sessao.query.filter(
                Sessao.psicologo_id == current_user.id,
                Sessao.status == 'realizada',
                func.date(Sessao.data_sessao) >= inicio_semana,
                func.date(Sessao.data_sessao) <= fim_semana
            ).count()
            
            agendadas = Sessao.query.filter(
                Sessao.psicologo_id == current_user.id,
                Sessao.status == 'agendada',
                func.date(Sessao.data_sessao) >= inicio_semana,
                func.date(Sessao.data_sessao) <= fim_semana
            ).count()
            
            semanas.insert(0, f"{inicio_semana.strftime('%d/%m')}")
            sessoes_realizadas.insert(0, realizadas)
            sessoes_agendadas.insert(0, agendadas)
        
        return jsonify({
            'labels': semanas,
            'datasets': [
                {
                    'label': 'Realizadas',
                    'data': sessoes_realizadas,
                    'borderColor': '#28a745',
                    'backgroundColor': 'rgba(40, 167, 69, 0.1)',
                    'fill': True
                },
                {
                    'label': 'Agendadas',
                    'data': sessoes_agendadas,
                    'borderColor': '#007bff',
                    'backgroundColor': 'rgba(0, 123, 255, 0.1)',
                    'fill': True
                }
            ]
        })
    except Exception as e:
        print(f"❌ Erro na API evolução sessões: {e}")
        return jsonify({'error': 'Erro ao buscar dados'}), 500

@app.route('/api/relatorios/top-pacientes')
@login_required
def api_top_pacientes():
    try:
        periodo = int(request.args.get('periodo', 12))
        hoje = date.today()
        data_inicio = hoje - timedelta(days=periodo*30)
        
        top_pacientes = db.session.query(
            Paciente.nome,
            func.count(Sessao.id).label('total_sessoes'),
            func.sum(Sessao.valor).label('total_receita')
        ).join(Sessao).filter(
            Sessao.psicologo_id == current_user.id,
            func.date(Sessao.data_sessao) >= data_inicio,
            Sessao.status == 'realizada'
        ).group_by(Paciente.id, Paciente.nome).order_by(
            func.count(Sessao.id).desc()
        ).limit(5).all()
        
        pacientes = []
        for nome, total_sessoes, total_receita in top_pacientes:
            pacientes.append({
                'nome': nome,
                'sessoes': total_sessoes,
                'receita': float(total_receita or 0)
            })
        
        return jsonify({'pacientes': pacientes})
    except Exception as e:
        print(f"❌ Erro na API top pacientes: {e}")
        return jsonify({'error': 'Erro ao buscar dados'}), 500

# ========== ROTA DE DEBUG ==========

@app.route('/debug/rotas')
@login_required
def debug_rotas():
    """Rota para listar todas as rotas disponíveis"""
    rotas = []
    for rule in app.url_map.iter_rules():
        rotas.append({
            'endpoint': rule.endpoint,
            'methods': ','.join(rule.methods),
            'path': str(rule)
        })
    return jsonify(rotas)

# ========== INICIALIZAÇÃO ==========

with app.app_context():
    try:
        db.create_all()
        print("=" * 60)
        print("✅ Tabelas criadas/verificadas com sucesso!")
        print("✅ Nova tabela 'configuracoes' adicionada!")
        print("✅ Campos de prontuário adicionados à tabela 'evolucoes'!")
        print("=" * 60)
        print("\n🔗 ROTAS REGISTRADAS:")
        print("   - /dashboard")
        print("   - /pacientes")
        print("   - /sessoes")
        print("   - /evolucoes")
        print("   - /relatorios")
        print("   - /configuracoes")
        print("   - /prontuario/<id>")
        print("=" * 60)
    except Exception as e:
        print("=" * 60)
        print(f"❌ Erro ao criar tabelas: {e}")
        traceback.print_exc()
        print("=" * 60)

if __name__ == '__main__':
    app.run(debug=True)

