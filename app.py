import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime, date, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from decimal import Decimal

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
    
    # Relacionamentos
    sessoes = db.relationship('Sessao', backref='paciente', lazy=True)

class Sessao(db.Model):
    __tablename__ = 'sessoes'
    
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    psicologo_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    data_sessao = db.Column(db.DateTime, nullable=False)
    duracao = db.Column(db.Integer, default=50)
    valor = db.Column(db.Numeric(10, 2))
    status = db.Column(db.String(20), default='agendada')  # agendada, realizada, cancelada, faltou
    observacoes = db.Column(db.Text)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    psicologo = db.relationship('Usuario', backref='sessoes_psicologo', lazy=True)

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
    # Estatísticas básicas
    total_pacientes = 0
    sessoes_hoje = 0
    proximas_sessoes = []
    sessoes_mes = 0
    receita_mes = 0
    
    try:
        # Buscar dados reais do banco
        total_pacientes = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).count()
        
        # Sessões hoje
        hoje = date.today()
        sessoes_hoje = Sessao.query.filter_by(psicologo_id=current_user.id).filter(
            db.func.date(Sessao.data_sessao) == hoje
        ).count()
        
        # Próximas sessões (próximos 7 dias)
        proximas_sessoes = Sessao.query.filter_by(
            psicologo_id=current_user.id,
            status='agendada'
        ).filter(
            Sessao.data_sessao >= datetime.now(),
            Sessao.data_sessao <= datetime.now() + timedelta(days=7)
        ).order_by(Sessao.data_sessao).limit(5).all()
        
        # Sessões este mês
        primeiro_dia_mes = hoje.replace(day=1)
        sessoes_mes = Sessao.query.filter_by(psicologo_id=current_user.id).filter(
            db.func.date(Sessao.data_sessao) >= primeiro_dia_mes,
            Sessao.status.in_(['realizada', 'agendada'])
        ).count()
        
        # Receita este mês (apenas sessões realizadas)
        receita_query = db.session.query(db.func.sum(Sessao.valor)).filter_by(
            psicologo_id=current_user.id,
            status='realizada'
        ).filter(
            db.func.date(Sessao.data_sessao) >= primeiro_dia_mes
        ).scalar()
        receita_mes = float(receita_query) if receita_query else 0
        
    except Exception as e:
        print(f"Erro ao buscar estatísticas: {e}")
        # Usar valores padrão se houver erro
        pass
    
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
    try:
        search = request.args.get('search', '')
        
        # Buscar pacientes com filtro de busca
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
        
        # Estatísticas
        total_pacientes = Paciente.query.filter_by(psicologo_id=current_user.id).count()
        pacientes_ativos = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).count()
        
        # Novos pacientes este mês
        primeiro_dia_mes = date.today().replace(day=1)
        novos_mes = Paciente.query.filter_by(psicologo_id=current_user.id).filter(
            Paciente.data_cadastro >= primeiro_dia_mes
        ).count()
        
        # Sessões este mês
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
                             evolucoes=evolucoes,
                             today=date.today())
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
                return render_template('editar_paciente.html', paciente=paciente, today=date.today())
            
            # Converter data de nascimento
            data_nascimento = None
            if data_nascimento_str:
                try:
                    data_nascimento = datetime.strptime(data_nascimento_str, '%Y-%m-%d').date()
                except:
                    flash('Data de nascimento inválida', 'error')
                    return render_template('editar_paciente.html', paciente=paciente, today=date.today())
            
            # Verificar se email já existe (se fornecido e diferente do atual)
            if email and email != paciente.email:
                paciente_existente = Paciente.query.filter_by(email=email, psicologo_id=current_user.id).first()
                if paciente_existente:
                    flash('Já existe um paciente com este email', 'error')
                    return render_template('editar_paciente.html', paciente=paciente, today=date.today())
            
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
        
        return render_template('editar_paciente.html', paciente=paciente, today=date.today())
        
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

# ========== ROTAS DE SESSÕES ==========

@app.route('/sessoes')
@login_required
def sessoes():
    try:
        # Filtros
        status_filter = request.args.get('status', '')
        paciente_filter = request.args.get('paciente', '')
        data_inicio = request.args.get('data_inicio', '')
        data_fim = request.args.get('data_fim', '')
        
        # Query base
        query = Sessao.query.filter_by(psicologo_id=current_user.id)
        
        # Aplicar filtros
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
        
        # Buscar sessões
        sessoes_lista = query.order_by(Sessao.data_sessao.desc()).all()
        
        # Buscar pacientes para o filtro
        pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).order_by(Paciente.nome).all()
        
        # Estatísticas
        total_sessoes = Sessao.query.filter_by(psicologo_id=current_user.id).count()
        sessoes_agendadas = Sessao.query.filter_by(psicologo_id=current_user.id, status='agendada').count()
        sessoes_realizadas = Sessao.query.filter_by(psicologo_id=current_user.id, status='realizada').count()
        
        # Receita total (sessões realizadas)
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
        print(f"Erro na página de sessões: {e}")
        flash('Erro ao carregar sessões', 'error')
        return redirect(url_for('dashboard'))

@app.route('/sessoes/nova', methods=['GET', 'POST'])
@login_required
def nova_sessao():
    if request.method == 'POST':
        try:
            print("=== DEBUG NOVA SESSÃO ===")
            
            # Capturar dados do formulário
            paciente_id = request.form.get('paciente_id')
            data_sessao_str = request.form.get('data_sessao')
            hora_sessao = request.form.get('hora_sessao')
            duracao = request.form.get('duracao', 50)
            valor_str = request.form.get('valor', '').strip()
            observacoes = request.form.get('observacoes', '').strip()
            
            print(f"Paciente ID: {paciente_id}")
            print(f"Data: {data_sessao_str}")
            print(f"Hora: {hora_sessao}")
            print(f"Duração: {duracao}")
            print(f"Valor string: '{valor_str}'")
            print(f"Observações: {observacoes}")
            
            # Validações básicas
            if not paciente_id:
                print("ERRO: Paciente não selecionado")
                flash('Paciente é obrigatório', 'error')
                pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).order_by(Paciente.nome).all()
                return render_template('nova_sessao.html', pacientes=pacientes_lista)
            
            if not data_sessao_str or not hora_sessao:
                print("ERRO: Data ou hora não fornecida")
                flash('Data e hora são obrigatórios', 'error')
                pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).order_by(Paciente.nome).all()
                return render_template('nova_sessao.html', pacientes=pacientes_lista)
            
            # Converter data e hora
            try:
                data_sessao = datetime.strptime(f"{data_sessao_str} {hora_sessao}", '%Y-%m-%d %H:%M')
                print(f"Data/hora convertida: {data_sessao}")
            except Exception as e:
                print(f"ERRO ao converter data/hora: {e}")
                flash('Data ou hora inválida', 'error')
                pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).order_by(Paciente.nome).all()
                return render_template('nova_sessao.html', pacientes=pacientes_lista)
            
            # Verificar se a data não é no passado
            if data_sessao < datetime.now():
                print("ERRO: Data no passado")
                flash('Não é possível agendar sessão no passado', 'error')
                pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).order_by(Paciente.nome).all()
                return render_template('nova_sessao.html', pacientes=pacientes_lista)
            
            # Verificar conflito de horário
            try:
                conflito = Sessao.query.filter_by(
                    psicologo_id=current_user.id,
                    status='agendada'
                ).filter(
                    Sessao.data_sessao == data_sessao
                ).first()
                
                if conflito:
                    print("ERRO: Conflito de horário")
                    flash('Já existe uma sessão agendada para este horário', 'error')
                    pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).order_by(Paciente.nome).all()
                    return render_template('nova_sessao.html', pacientes=pacientes_lista)
            except Exception as e:
                print(f"ERRO ao verificar conflito: {e}")
            
            # Converter valor
            valor = None
            if valor_str and valor_str.strip():
                try:
                    # Limpar e converter valor
                    valor_limpo = valor_str.replace(',', '.').strip()
                    valor = Decimal(valor_limpo)
                    print(f"Valor convertido: {valor}")
                except Exception as e:
                    print(f"ERRO ao converter valor '{valor_str}': {e}")
                    flash('Valor inválido', 'error')
                    pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).order_by(Paciente.nome).all()
                    return render_template('nova_sessao.html', pacientes=pacientes_lista)
            
            # Verificar se paciente existe e pertence ao usuário
            try:
                paciente = Paciente.query.filter_by(id=paciente_id, psicologo_id=current_user.id).first()
                if not paciente:
                    print("ERRO: Paciente não encontrado ou não pertence ao usuário")
                    flash('Paciente não encontrado', 'error')
                    pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).order_by(Paciente.nome).all()
                    return render_template('nova_sessao.html', pacientes=pacientes_lista)
                print(f"Paciente encontrado: {paciente.nome}")
            except Exception as e:
                print(f"ERRO ao buscar paciente: {e}")
                flash('Erro ao verificar paciente', 'error')
                pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).order_by(Paciente.nome).all()
                return render_template('nova_sessao.html', pacientes=pacientes_lista)
            
            # Criar nova sessão
            try:
                nova_sessao_obj = Sessao(
                    paciente_id=int(paciente_id),
                    psicologo_id=current_user.id,
                    data_sessao=data_sessao,
                    duracao=int(duracao),
                    valor=valor,
                    observacoes=observacoes if observacoes else None
                )
                
                print(f"Sessão criada: {nova_sessao_obj}")
                print(f"Paciente ID: {nova_sessao_obj.paciente_id}")
                print(f"Psicólogo ID: {nova_sessao_obj.psicologo_id}")
                print(f"Data: {nova_sessao_obj.data_sessao}")
                print(f"Valor: {nova_sessao_obj.valor}")
                
                db.session.add(nova_sessao_obj)
                db.session.commit()
                
                print("Sessão salva no banco com sucesso!")
                
                flash(f'Sessão agendada com {paciente.nome} para {data_sessao.strftime("%d/%m/%Y às %H:%M")}!', 'success')
                return redirect(url_for('sessoes'))
                
            except Exception as e:
                print(f"ERRO ao salvar sessão no banco: {e}")
                print(f"Tipo do erro: {type(e)}")
                import traceback
                traceback.print_exc()
                flash('Erro ao salvar sessão no banco de dados', 'error')
                db.session.rollback()
                pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).order_by(Paciente.nome).all()
                return render_template('nova_sessao.html', pacientes=pacientes_lista)
            
        except Exception as e:
            print(f"ERRO GERAL na nova_sessao: {e}")
            print(f"Tipo do erro: {type(e)}")
            import traceback
            traceback.print_exc()
            flash('Erro ao agendar sessão', 'error')
            db.session.rollback()
    
    # Buscar pacientes ativos para o formulário
    try:
        pacientes_lista = Paciente.query.filter_by(psicologo_id=current_user.id, ativo=True).order_by(Paciente.nome).all()
        print(f"Pacientes encontrados: {len(pacientes_lista)}")
    except Exception as e:
        print(f"ERRO ao buscar pacientes: {e}")
        pacientes_lista = []
    
    return render_template('nova_sessao.html', pacientes=pacientes_lista)

@app.route('/sessoes/<int:id>')
@login_required
def ver_sessao(id):
    try:
        sessao = Sessao.query.filter_by(id=id, psicologo_id=current_user.id).first_or_404()
        return render_template('ver_sessao.html', sessao=sessao, today=date.today())
    except Exception as e:
        print(f"Erro ao ver sessão: {e}")
        flash('Sessão não encontrada', 'error')
        return redirect(url_for('sessoes'))

@app.route('/sessoes/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_sessao(id):
    try:
        sessao = Sessao.query.filter_by(id=id, psicologo_id=current_user.id).first_or_404()
        
        if request.method == 'POST':
            # Capturar dados do formulário
            data_sessao_str = request.form.get('data_sessao')
            hora_sessao = request.form.get('hora_sessao')
            duracao = request.form.get('duracao', 50)
            valor_str = request.form.get('valor', '').strip()
            observacoes = request.form.get('observacoes', '').strip()
            
            # Validações básicas
            if not data_sessao_str or not hora_sessao:
                flash('Data e hora são obrigatórios', 'error')
                return render_template('editar_sessao.html', sessao=sessao, today=date.today())
            
            # Converter data e hora
            try:
                data_sessao = datetime.strptime(f"{data_sessao_str} {hora_sessao}", '%Y-%m-%d %H:%M')
            except:
                flash('Data ou hora inválida', 'error')
                return render_template('editar_sessao.html', sessao=sessao, today=date.today())
            
            # Verificar conflito de horário (exceto a própria sessão)
            conflito = Sessao.query.filter_by(
                psicologo_id=current_user.id,
                status='agendada'
            ).filter(
                Sessao.data_sessao == data_sessao,
                Sessao.id != id
            ).first()
            
            if conflito:
                flash('Já existe uma sessão agendada para este horário', 'error')
                return render_template('editar_sessao.html', sessao=sessao, today=date.today())
            
            # Converter valor
            valor = None
            if valor_str and valor_str.strip():
                try:
                    valor = Decimal(valor_str.replace(',', '.'))
                except:
                    flash('Valor inválido', 'error')
                    return render_template('editar_sessao.html', sessao=sessao, today=date.today())
            
            # Atualizar sessão
            sessao.data_sessao = data_sessao
            sessao.duracao = int(duracao)
            sessao.valor = valor
            sessao.observacoes = observacoes if observacoes else None
            
            db.session.commit()
            
            flash('Sessão atualizada com sucesso!', 'success')
            return redirect(url_for('ver_sessao', id=id))
        
        return render_template('editar_sessao.html', sessao=sessao, today=date.today())
        
    except Exception as e:
        print(f"Erro ao editar sessão: {e}")
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
        print(f"Erro ao marcar sessão como realizada: {e}")
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
        print(f"Erro ao marcar sessão como falta: {e}")
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
        print(f"Erro ao cancelar sessão: {e}")
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
        print(f"Erro ao reagendar sessão: {e}")
        return jsonify({'success': False, 'message': 'Erro ao reagendar sessão'})

# ========== FIM DAS ROTAS DE SESSÕES ==========

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
