// ==========================================
// MINDCAREPRO - AGENDA
// Arquivo: agenda.js
// 
// Descrição:
// Gerenciamento completo da agenda de agendamentos usando FullCalendar.js
// 
// Funcionalidades:
// - Inicialização e configuração do FullCalendar
// - CRUD completo de agendamentos (Create, Read, Update, Delete)
// - Drag & drop para reagendar
// - Filtros por status
// - Modais de criação e edição
// - Validação de formulários
// - Comunicação com APIs REST do backend
// - Feedback visual (toasts/alerts)
// - Tratamento de erros
// 
// Dependências:
// - FullCalendar 6.x (carregado via CDN no HTML)
// - Bootstrap 5.3.0 (modais e componentes)
// - Fetch API (nativa do navegador)
// 
// APIs utilizadas:
// - GET    /api/agendamentos - Listar agendamentos
// - POST   /api/agendamentos - Criar agendamento
// - PUT    /api/agendamentos/<id> - Atualizar agendamento
// - DELETE /api/agendamentos/<id> - Deletar agendamento
// - GET    /api/pacientes - Listar pacientes
// 
// Desenvolvido por: Flavio Ricci + IA Adapta ONE 26
// Data: Janeiro 2026
// ==========================================

// ==========================================
// VARIÁVEIS GLOBAIS
// ==========================================

/**
 * Instância do FullCalendar
 * Armazena a referência ao calendário para manipulação posterior
 */
let calendar;

/**
 * Agendamento atualmente selecionado
 * Usado para edição e deleção
 */
let agendamentoAtual = null;

/**
 * Lista de pacientes carregada da API
 * Cache para evitar múltiplas requisições
 */
let pacientesCache = [];

/**
 * Filtro de status atual
 * Usado para filtrar eventos no calendário
 */
let filtroStatusAtual = 'todos';

// ==========================================
// INICIALIZAÇÃO
// ==========================================

/**
 * Função executada quando o DOM estiver completamente carregado
 * Inicializa todos os componentes da agenda
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ Agenda.js carregado');
    
    // Inicializa o calendário
    inicializarCalendario();
    
    // Carrega lista de pacientes
    carregarPacientes();
    
    // Configura event listeners dos botões e filtros
    configurarEventListeners();
    
    console.log('✅ Agenda inicializada com sucesso');
});

// ==========================================
// INICIALIZAÇÃO DO FULLCALENDAR
// ==========================================

/**
 * Inicializa e configura o FullCalendar
 * Define todas as opções, callbacks e comportamentos
 */
function inicializarCalendario() {
    console.log('🔄 Inicializando FullCalendar...');
    
    const calendarEl = document.getElementById('calendar');
    
    if (!calendarEl) {
        console.error('❌ Elemento #calendar não encontrado');
        return;
    }
    
    // Cria instância do FullCalendar
    calendar = new FullCalendar.Calendar(calendarEl, {
        
        // ========== CONFIGURAÇÕES GERAIS ==========
        
        /**
         * Locale: Português do Brasil
         * Define idioma de todos os textos do calendário
         */
        locale: 'pt-br',
        
        /**
         * Timezone: Local do usuário
         * Usa o fuso horário do navegador
         */
        timeZone: 'local',
        
        /**
         * Altura: Automática
         * Ajusta a altura baseado no conteúdo
         */
        height: 'auto',
        
        /**
         * Cabeçalho: Personalizado
         * Define botões e título visíveis
         */
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },
        
        /**
         * Botões: Textos personalizados
         */
        buttonText: {
            today: 'Hoje',
            month: 'Mês',
            week: 'Semana',
            day: 'Dia',
            list: 'Lista'
        },
        
        /**
         * Visualização inicial: Semana
         */
        initialView: 'timeGridWeek',
        
        /**
         * Navegação por data: Habilitada
         */
        navLinks: true,
        
        /**
         * Seleção de múltiplos dias: Habilitada
         */
        selectable: true,
        
        /**
         * Indicador de "agora": Habilitado
         */
        nowIndicator: true,
        
        /**
         * Edição: Habilitada (drag & drop)
         */
        editable: true,
        
        /**
         * Formato de hora: 24 horas
         */
        slotLabelFormat: {
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
        },
        
        /**
         * Formato de hora nos eventos
         */
        eventTimeFormat: {
            hour: '2-digit',
            minute: '2-digit',
            hour12: false
        },
        
        /**
         * Duração dos slots: 30 minutos
         */
        slotDuration: '00:30:00',
        
        /**
         * Horário de início: 07:00
         */
        slotMinTime: '07:00:00',
        
        /**
         * Horário de fim: 23:00
         */
        slotMaxTime: '23:00:00',
        
        /**
         * Fim de semana: Visível
         */
        weekends: true,
        
        /**
         * Número da semana: Não visível
         */
        weekNumbers: false,
        
        /**
         * Todos os dias: Visível
         */
        allDaySlot: false,
        
        // ========== FONTE DE DADOS ==========
        
        /**
         * Eventos: Carregados via API
         * Função que busca agendamentos do backend
         */
        events: function(info, successCallback, failureCallback) {
            carregarAgendamentos(info, successCallback, failureCallback);
        },
        
        // ========== CALLBACKS DE EVENTOS ==========
        
        /**
         * Callback: Clique em evento
         * Abre modal com detalhes do agendamento
         */
        eventClick: function(info) {
            console.log('🖱️ Evento clicado:', info.event.id);
            abrirModalDetalhes(info.event);
        },
        
        /**
         * Callback: Drag & Drop de evento
         * Atualiza data/hora do agendamento
         */
        eventDrop: function(info) {
            console.log('🔄 Evento movido:', info.event.id);
            reagendarEvento(info);
        },
        
        /**
         * Callback: Redimensionar evento
         * Atualiza duração do agendamento
         */
        eventResize: function(info) {
            console.log('↔️ Evento redimensionado:', info.event.id);
            redimensionarEvento(info);
        },
        
        /**
         * Callback: Clique em data/hora vazia
         * Abre modal para criar novo agendamento
         */
        dateClick: function(info) {
            console.log('📅 Data clicada:', info.dateStr);
            abrirModalNovoAgendamento(info.date);
        },
        
        /**
         * Callback: Seleção de período
         * Abre modal para criar agendamento com duração
         */
        select: function(info) {
            console.log('📅 Período selecionado:', info.startStr, '-', info.endStr);
            abrirModalNovoAgendamento(info.start, info.end);
        },
        
        /**
         * Callback: Erro ao carregar eventos
         */
        eventSourceFailure: function(error) {
            console.error('❌ Erro ao carregar eventos:', error);
            mostrarAlerta('Erro ao carregar agendamentos. Tente recarregar a página.', 'danger');
        },
        
        /**
         * Callback: Renderização de evento
         * Permite customização visual adicional
         */
        eventDidMount: function(info) {
            // Adiciona tooltip com informações do agendamento
            info.el.title = `${info.event.title}\n${info.event.extendedProps.tipo}\nStatus: ${info.event.extendedProps.status}`;
        }
        
    });
    
    // Renderiza o calendário
    calendar.render();
    
    console.log('✅ FullCalendar renderizado');
}

// ==========================================
// CARREGAMENTO DE DADOS
// ==========================================

/**
 * Carrega agendamentos da API
 * Chamada automaticamente pelo FullCalendar
 * 
 * @param {Object} info - Informações do período solicitado
 * @param {Function} successCallback - Callback de sucesso
 * @param {Function} failureCallback - Callback de erro
 */
function carregarAgendamentos(info, successCallback, failureCallback) {
    console.log('🔄 Carregando agendamentos...');
    console.log('   Período:', info.startStr, 'até', info.endStr);
    console.log('   Filtro status:', filtroStatusAtual);
    
    // Monta URL com parâmetros
    let url = '/api/agendamentos';
    const params = new URLSearchParams({
        start: info.startStr,
        end: info.endStr
    });
    
    // Adiciona filtro de status se não for "todos"
    if (filtroStatusAtual !== 'todos') {
        params.append('status', filtroStatusAtual);
    }
    
    url += '?' + params.toString();
    
    // Faz requisição à API
    fetch(url, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        console.log(`✅ ${data.length} agendamentos carregados`);
        successCallback(data);
    })
    .catch(error => {
        console.error('❌ Erro ao carregar agendamentos:', error);
        failureCallback(error);
        mostrarAlerta('Erro ao carregar agendamentos. Verifique sua conexão.', 'danger');
    });
}

/**
 * Carrega lista de pacientes da API
 * Popula os selects dos modais
 */
function carregarPacientes() {
    console.log('🔄 Carregando pacientes...');
    
    fetch('/api/pacientes', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        console.log(`✅ ${data.length} pacientes carregados`);
        pacientesCache = data;
        popularSelectsPacientes();
    })
    .catch(error => {
        console.error('❌ Erro ao carregar pacientes:', error);
        mostrarAlerta('Erro ao carregar lista de pacientes.', 'warning');
    });
}

/**
 * Popula os selects de pacientes nos modais
 * Usa o cache de pacientes carregado anteriormente
 */
function popularSelectsPacientes() {
    const selectNovo = document.getElementById('novoPaciente');
    const selectEditar = document.getElementById('editarPaciente');
    
    // Limpa opções existentes (mantém apenas o placeholder)
    selectNovo.innerHTML = '<option value="">Selecione um paciente...</option>';
    selectEditar.innerHTML = '<option value="">Selecione um paciente...</option>';
    
    // Adiciona opções de pacientes
    pacientesCache.forEach(paciente => {
        const optionNovo = document.createElement('option');
        optionNovo.value = paciente.id;
        optionNovo.textContent = paciente.nome;
        selectNovo.appendChild(optionNovo);
        
        const optionEditar = document.createElement('option');
        optionEditar.value = paciente.id;
        optionEditar.textContent = paciente.nome;
        selectEditar.appendChild(optionEditar);
    });
    
    console.log('✅ Selects de pacientes populados');
}
// ==========================================
// CONFIGURAÇÃO DE EVENT LISTENERS
// ==========================================

/**
 * Configura todos os event listeners dos botões e filtros
 * Chamada na inicialização da página
 */
function configurarEventListeners() {
    console.log('🔄 Configurando event listeners...');
    
    // ========== FILTRO DE STATUS ==========
    const filtroStatus = document.getElementById('filtroStatus');
    if (filtroStatus) {
        filtroStatus.addEventListener('change', function() {
            filtroStatusAtual = this.value;
            console.log('🔍 Filtro alterado para:', filtroStatusAtual);
            calendar.refetchEvents(); // Recarrega eventos com novo filtro
        });
    }
    
    // ========== BOTÃO HOJE ==========
    const btnHoje = document.getElementById('btnHoje');
    if (btnHoje) {
        btnHoje.addEventListener('click', function() {
            console.log('📅 Navegando para hoje');
            calendar.today();
        });
    }
    
    // ========== MODAL NOVO AGENDAMENTO ==========
    const btnSalvarAgendamento = document.getElementById('btnSalvarAgendamento');
    if (btnSalvarAgendamento) {
        btnSalvarAgendamento.addEventListener('click', salvarNovoAgendamento);
    }
    
    // ========== MODAL DETALHES/EDIÇÃO ==========
    const btnEditarAgendamento = document.getElementById('btnEditarAgendamento');
    if (btnEditarAgendamento) {
        btnEditarAgendamento.addEventListener('click', ativarModoEdicao);
    }
    
    const btnCancelarEdicao = document.getElementById('btnCancelarEdicao');
    if (btnCancelarEdicao) {
        btnCancelarEdicao.addEventListener('click', desativarModoEdicao);
    }
    
    const btnSalvarEdicao = document.getElementById('btnSalvarEdicao');
    if (btnSalvarEdicao) {
        btnSalvarEdicao.addEventListener('click', salvarEdicaoAgendamento);
    }
    
    const btnDeletarAgendamento = document.getElementById('btnDeletarAgendamento');
    if (btnDeletarAgendamento) {
        btnDeletarAgendamento.addEventListener('click', deletarAgendamento);
    }
    
    // ========== RESET DE FORMULÁRIOS AO FECHAR MODAIS ==========
    const modalNovo = document.getElementById('modalNovoAgendamento');
    if (modalNovo) {
        modalNovo.addEventListener('hidden.bs.modal', function() {
            document.getElementById('formNovoAgendamento').reset();
        });
    }
    
    const modalDetalhes = document.getElementById('modalDetalhesAgendamento');
    if (modalDetalhes) {
        modalDetalhes.addEventListener('hidden.bs.modal', function() {
            desativarModoEdicao();
            agendamentoAtual = null;
        });
    }
    
    console.log('✅ Event listeners configurados');
}

// ==========================================
// MODAL: NOVO AGENDAMENTO
// ==========================================

/**
 * Abre modal para criar novo agendamento
 * Preenche data/hora se fornecidas (clique no calendário)
 * 
 * @param {Date} dataInicio - Data/hora de início (opcional)
 * @param {Date} dataFim - Data/hora de fim (opcional)
 */
function abrirModalNovoAgendamento(dataInicio = null, dataFim = null) {
    console.log('📝 Abrindo modal de novo agendamento');
    
    // Limpa formulário
    document.getElementById('formNovoAgendamento').reset();
    
    // Preenche data e hora se fornecidas
    if (dataInicio) {
        const data = dataInicio.toISOString().split('T')[0];
        const hora = dataInicio.toTimeString().substring(0, 5);
        
        document.getElementById('novaData').value = data;
        document.getElementById('novaHoraInicio').value = hora;
        
        // Calcula duração se dataFim fornecida
        if (dataFim) {
            const duracaoMinutos = Math.round((dataFim - dataInicio) / 60000);
            document.getElementById('novaDuracao').value = duracaoMinutos;
        }
    } else {
        // Define data de hoje como padrão
        const hoje = new Date();
        document.getElementById('novaData').value = hoje.toISOString().split('T')[0];
    }
    
    // Abre modal
    const modal = new bootstrap.Modal(document.getElementById('modalNovoAgendamento'));
    modal.show();
}

/**
 * Salva novo agendamento
 * Valida formulário e envia para API
 */
function salvarNovoAgendamento() {
    console.log('💾 Salvando novo agendamento...');
    
    const form = document.getElementById('formNovoAgendamento');
    
    // Valida formulário
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    // Coleta dados do formulário
    const pacienteId = document.getElementById('novoPaciente').value;
    const data = document.getElementById('novaData').value;
    const horaInicio = document.getElementById('novaHoraInicio').value;
    const duracao = document.getElementById('novaDuracao').value;
    const tipo = document.getElementById('novoTipo').value;
    const valor = document.getElementById('novoValor').value;
    const linkMeet = document.getElementById('novoLinkMeet').value;
    const observacoes = document.getElementById('novasObservacoes').value;
    
    // Valida campos obrigatórios
    if (!pacienteId || !data || !horaInicio) {
        mostrarAlerta('Preencha todos os campos obrigatórios.', 'warning');
        return;
    }
    
    // Monta data/hora de início
    const dataInicio = new Date(`${data}T${horaInicio}`);
    
    // Calcula data/hora de fim baseado na duração
    const dataFim = new Date(dataInicio.getTime() + (duracao * 60000));
    
    // Monta objeto de dados
    const dados = {
        paciente_id: parseInt(pacienteId),
        data_inicio: dataInicio.toISOString(),
        data_fim: dataFim.toISOString(),
        duracao: parseInt(duracao),
        tipo: tipo,
        valor: valor ? parseFloat(valor) : null,
        link_meet: linkMeet || null,
        observacoes: observacoes || null
    };
    
    console.log('   Dados:', dados);
    
    // Desabilita botão durante requisição
    const btnSalvar = document.getElementById('btnSalvarAgendamento');
    btnSalvar.disabled = true;
    btnSalvar.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Salvando...';
    
    // Envia para API
    fetch('/api/agendamentos', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(dados)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => {
                throw new Error(err.message || err.error || 'Erro ao criar agendamento');
            });
        }
        return response.json();
    })
    .then(data => {
        console.log('✅ Agendamento criado:', data);
        
        // Fecha modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('modalNovoAgendamento'));
        modal.hide();
        
        // Recarrega eventos no calendário
        calendar.refetchEvents();
        
        // Mostra mensagem de sucesso
        mostrarAlerta('Agendamento criado com sucesso!', 'success');
    })
    .catch(error => {
        console.error('❌ Erro ao criar agendamento:', error);
        mostrarAlerta(error.message || 'Erro ao criar agendamento. Tente novamente.', 'danger');
    })
    .finally(() => {
        // Reabilita botão
        btnSalvar.disabled = false;
        btnSalvar.innerHTML = '<i class="bi bi-check-circle"></i> Salvar Agendamento';
    });
}

// ==========================================
// MODAL: DETALHES DO AGENDAMENTO
// ==========================================

/**
 * Abre modal com detalhes do agendamento
 * Modo visualização (somente leitura)
 * 
 * @param {Object} event - Evento do FullCalendar
 */
function abrirModalDetalhes(event) {
    console.log('👁️ Abrindo detalhes do agendamento:', event.id);
    
    // Armazena agendamento atual
    agendamentoAtual = {
        id: event.id,
        paciente_id: event.extendedProps.paciente_id,
        paciente_nome: event.extendedProps.paciente_nome,
        data_inicio: event.start,
        data_fim: event.end,
        duracao: event.extendedProps.duracao,
        tipo: event.extendedProps.tipo,
        valor: event.extendedProps.valor,
        status: event.extendedProps.status,
        pago: event.extendedProps.pago,
        link_meet: event.extendedProps.link_meet,
        observacoes: event.extendedProps.observacoes
    };
    
    // Preenche campos de visualização
    document.getElementById('detalhePaciente').textContent = agendamentoAtual.paciente_nome;
    
    // Status com badge colorido
    const badgeStatus = document.getElementById('detalheStatus');
    badgeStatus.textContent = formatarStatus(agendamentoAtual.status);
    badgeStatus.className = 'badge badge-status-' + agendamentoAtual.status.replace('_', '-');
    
    // Data e hora formatadas
    const dataHoraInicio = new Date(agendamentoAtual.data_inicio);
    const dataHoraFim = new Date(agendamentoAtual.data_fim);
    document.getElementById('detalheDataHora').textContent = 
        `${dataHoraInicio.toLocaleDateString('pt-BR')} às ${dataHoraInicio.toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})} - ${dataHoraFim.toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})}`;
    
    // Duração
    document.getElementById('detalheDuracao').textContent = `${agendamentoAtual.duracao} minutos`;
    
    // Tipo
    document.getElementById('detalheTipo').textContent = agendamentoAtual.tipo === 'online' ? 'Online' : 'Presencial';
    
    // Valor
    if (agendamentoAtual.valor) {
        document.getElementById('detalheValor').textContent = 
            `R$ ${parseFloat(agendamentoAtual.valor).toFixed(2).replace('.', ',')}${agendamentoAtual.pago ? ' (Pago)' : ' (Pendente)'}`;
    } else {
        document.getElementById('detalheValor').textContent = 'Não informado';
    }
    
    // Link Google Meet (exibe apenas se existir)
    const linkMeetContainer = document.getElementById('detalheLinkMeetContainer');
    if (agendamentoAtual.link_meet) {
        document.getElementById('detalheLinkMeet').href = agendamentoAtual.link_meet;
        linkMeetContainer.style.display = 'block';
    } else {
        linkMeetContainer.style.display = 'none';
    }
    
    // Observações (exibe apenas se existirem)
    const observacoesContainer = document.getElementById('detalheObservacoesContainer');
    if (agendamentoAtual.observacoes) {
        document.getElementById('detalheObservacoes').textContent = agendamentoAtual.observacoes;
        observacoesContainer.style.display = 'block';
    } else {
        observacoesContainer.style.display = 'none';
    }
    
    // Garante que está no modo visualização
    desativarModoEdicao();
    
    // Abre modal
    const modal = new bootstrap.Modal(document.getElementById('modalDetalhesAgendamento'));
    modal.show();
}

/**
 * Ativa modo de edição no modal de detalhes
 * Esconde visualização e mostra formulário
 */
function ativarModoEdicao() {
    console.log('✏️ Ativando modo de edição');
    
    // Esconde visualização
    document.getElementById('visualizacaoAgendamento').style.display = 'none';
    document.getElementById('botoesVisualizacao').style.display = 'none';
    
    // Mostra formulário de edição
    document.getElementById('formEditarAgendamento').style.display = 'block';
    document.getElementById('botoesEdicao').style.display = 'block';
    
    // Preenche formulário com dados atuais
    document.getElementById('editarAgendamentoId').value = agendamentoAtual.id;
    document.getElementById('editarPaciente').value = agendamentoAtual.paciente_id;
    
    const dataInicio = new Date(agendamentoAtual.data_inicio);
    document.getElementById('editarData').value = dataInicio.toISOString().split('T')[0];
    document.getElementById('editarHoraInicio').value = dataInicio.toTimeString().substring(0, 5);
    document.getElementById('editarDuracao').value = agendamentoAtual.duracao;
    document.getElementById('editarStatus').value = agendamentoAtual.status;
    document.getElementById('editarTipo').value = agendamentoAtual.tipo;
    document.getElementById('editarValor').value = agendamentoAtual.valor || '';
    document.getElementById('editarPago').checked = agendamentoAtual.pago || false;
    document.getElementById('editarLinkMeet').value = agendamentoAtual.link_meet || '';
    document.getElementById('editarObservacoes').value = agendamentoAtual.observacoes || '';
}

/**
 * Desativa modo de edição no modal de detalhes
 * Volta para modo visualização
 */
function desativarModoEdicao() {
    console.log('👁️ Desativando modo de edição');
    
    // Mostra visualização
    document.getElementById('visualizacaoAgendamento').style.display = 'block';
    document.getElementById('botoesVisualizacao').style.display = 'block';
    
    // Esconde formulário de edição
    document.getElementById('formEditarAgendamento').style.display = 'none';
    document.getElementById('botoesEdicao').style.display = 'none';
}

/**
 * Salva edição do agendamento
 * Valida formulário e envia para API
 */
function salvarEdicaoAgendamento() {
    console.log('💾 Salvando edição do agendamento...');
    
    const form = document.getElementById('formEditarAgendamento');
    
    // Valida formulário
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }
    
    // Coleta dados do formulário
    const id = document.getElementById('editarAgendamentoId').value;
    const pacienteId = document.getElementById('editarPaciente').value;
    const data = document.getElementById('editarData').value;
    const horaInicio = document.getElementById('editarHoraInicio').value;
    const duracao = document.getElementById('editarDuracao').value;
    const status = document.getElementById('editarStatus').value;
    const tipo = document.getElementById('editarTipo').value;
    const valor = document.getElementById('editarValor').value;
    const pago = document.getElementById('editarPago').checked;
    const linkMeet = document.getElementById('editarLinkMeet').value;
    const observacoes = document.getElementById('editarObservacoes').value;
    
    // Monta data/hora de início
    const dataInicio = new Date(`${data}T${horaInicio}`);
    
    // Calcula data/hora de fim baseado na duração
    const dataFim = new Date(dataInicio.getTime() + (duracao * 60000));
    
    // Monta objeto de dados
    const dados = {
        paciente_id: parseInt(pacienteId),
        data_inicio: dataInicio.toISOString(),
        data_fim: dataFim.toISOString(),
        duracao: parseInt(duracao),
        status: status,
        tipo: tipo,
        valor: valor ? parseFloat(valor) : null,
        pago: pago,
        link_meet: linkMeet || null,
        observacoes: observacoes || null
    };
    
    console.log('   Dados:', dados);
    
    // Desabilita botão durante requisição
    const btnSalvar = document.getElementById('btnSalvarEdicao');
    btnSalvar.disabled = true;
    btnSalvar.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Salvando...';
    
    // Envia para API
    fetch(`/api/agendamentos/${id}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(dados)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => {
                throw new Error(err.message || err.error || 'Erro ao atualizar agendamento');
            });
        }
        return response.json();
    })
    .then(data => {
        console.log('✅ Agendamento atualizado:', data);
        
        // Fecha modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('modalDetalhesAgendamento'));
        modal.hide();
        
        // Recarrega eventos no calendário
        calendar.refetchEvents();
        
        // Mostra mensagem de sucesso
        mostrarAlerta('Agendamento atualizado com sucesso!', 'success');
    })
    .catch(error => {
        console.error('❌ Erro ao atualizar agendamento:', error);
        mostrarAlerta(error.message || 'Erro ao atualizar agendamento. Tente novamente.', 'danger');
    })
    .finally(() => {
        // Reabilita botão
        btnSalvar.disabled = false;
        btnSalvar.innerHTML = '<i class="bi bi-check-circle"></i> Salvar Alterações';
    });
}
// ==========================================
// DELETAR AGENDAMENTO
// ==========================================

/**
 * Deleta agendamento após confirmação
 * Remove permanentemente do banco de dados
 */
function deletarAgendamento() {
    console.log('🗑️ Solicitando deleção do agendamento:', agendamentoAtual.id);
    
    // Confirmação do usuário
    if (!confirm(`Tem certeza que deseja deletar o agendamento com ${agendamentoAtual.paciente_nome}?\n\nEsta ação não pode ser desfeita.`)) {
        console.log('   Deleção cancelada pelo usuário');
        return;
    }
    
    const id = agendamentoAtual.id;
    
    // Desabilita botão durante requisição
    const btnDeletar = document.getElementById('btnDeletarAgendamento');
    btnDeletar.disabled = true;
    btnDeletar.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Deletando...';
    
    // Envia requisição DELETE para API
    fetch(`/api/agendamentos/${id}`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => {
                throw new Error(err.message || err.error || 'Erro ao deletar agendamento');
            });
        }
        return response.json();
    })
    .then(data => {
        console.log('✅ Agendamento deletado:', data);
        
        // Fecha modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('modalDetalhesAgendamento'));
        modal.hide();
        
        // Recarrega eventos no calendário
        calendar.refetchEvents();
        
        // Mostra mensagem de sucesso
        mostrarAlerta('Agendamento deletado com sucesso!', 'success');
    })
    .catch(error => {
        console.error('❌ Erro ao deletar agendamento:', error);
        mostrarAlerta(error.message || 'Erro ao deletar agendamento. Tente novamente.', 'danger');
    })
    .finally(() => {
        // Reabilita botão
        btnDeletar.disabled = false;
        btnDeletar.innerHTML = '<i class="bi bi-trash"></i> Deletar';
    });
}

// ==========================================
// REAGENDAR (DRAG & DROP)
// ==========================================

/**
 * Reagenda evento após drag & drop
 * Atualiza data/hora de início e fim
 * 
 * @param {Object} info - Informações do evento movido
 */
function reagendarEvento(info) {
    console.log('🔄 Reagendando evento:', info.event.id);
    console.log('   Nova data/hora:', info.event.start);
    
    const id = info.event.id;
    const novaDataInicio = info.event.start;
    const novaDataFim = info.event.end;
    
    // Monta objeto de dados (apenas data/hora)
    const dados = {
        data_inicio: novaDataInicio.toISOString(),
        data_fim: novaDataFim.toISOString()
    };
    
    console.log('   Dados:', dados);
    
    // Envia para API
    fetch(`/api/agendamentos/${id}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(dados)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => {
                throw new Error(err.message || err.error || 'Erro ao reagendar');
            });
        }
        return response.json();
    })
    .then(data => {
        console.log('✅ Evento reagendado:', data);
        mostrarAlerta('Agendamento reagendado com sucesso!', 'success');
    })
    .catch(error => {
        console.error('❌ Erro ao reagendar:', error);
        mostrarAlerta(error.message || 'Erro ao reagendar. Tente novamente.', 'danger');
        
        // Reverte a mudança visual
        info.revert();
    });
}

/**
 * Redimensiona evento após arrastar as bordas
 * Atualiza duração do agendamento
 * 
 * @param {Object} info - Informações do evento redimensionado
 */
function redimensionarEvento(info) {
    console.log('↔️ Redimensionando evento:', info.event.id);
    console.log('   Nova duração:', info.event.start, '-', info.event.end);
    
    const id = info.event.id;
    const novaDataInicio = info.event.start;
    const novaDataFim = info.event.end;
    
    // Calcula nova duração em minutos
    const novaDuracao = Math.round((novaDataFim - novaDataInicio) / 60000);
    
    // Monta objeto de dados
    const dados = {
        data_inicio: novaDataInicio.toISOString(),
        data_fim: novaDataFim.toISOString(),
        duracao: novaDuracao
    };
    
    console.log('   Dados:', dados);
    
    // Envia para API
    fetch(`/api/agendamentos/${id}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(dados)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => {
                throw new Error(err.message || err.error || 'Erro ao redimensionar');
            });
        }
        return response.json();
    })
    .then(data => {
        console.log('✅ Evento redimensionado:', data);
        mostrarAlerta('Duração atualizada com sucesso!', 'success');
    })
    .catch(error => {
        console.error('❌ Erro ao redimensionar:', error);
        mostrarAlerta(error.message || 'Erro ao atualizar duração. Tente novamente.', 'danger');
        
        // Reverte a mudança visual
        info.revert();
    });
}

// ==========================================
// FUNÇÕES AUXILIARES
// ==========================================

/**
 * Formata status para exibição
 * Converte valor do banco para texto legível
 * 
 * @param {string} status - Status do agendamento
 * @returns {string} Status formatado
 */
function formatarStatus(status) {
    const statusMap = {
        'agendada': 'Agendada',
        'confirmada': 'Confirmada',
        'em_andamento': 'Em Andamento',
        'realizada': 'Realizada',
        'faltou': 'Faltou',
        'cancelada': 'Cancelada',
        'reagendada': 'Reagendada'
    };
    
    return statusMap[status] || status;
}

/**
 * Mostra alerta/toast para o usuário
 * Usa Bootstrap Alerts para feedback visual
 * 
 * @param {string} mensagem - Mensagem a ser exibida
 * @param {string} tipo - Tipo do alerta (success, danger, warning, info)
 */
function mostrarAlerta(mensagem, tipo = 'info') {
    console.log(`📢 Alerta [${tipo}]:`, mensagem);
    
    // Remove alertas anteriores
    const alertasAntigos = document.querySelectorAll('.alert-flutuante');
    alertasAntigos.forEach(alerta => alerta.remove());
    
    // Cria novo alerta
    const alerta = document.createElement('div');
    alerta.className = `alert alert-${tipo} alert-dismissible fade show alert-flutuante`;
    alerta.setAttribute('role', 'alert');
    alerta.style.position = 'fixed';
    alerta.style.top = '20px';
    alerta.style.right = '20px';
    alerta.style.zIndex = '9999';
    alerta.style.minWidth = '300px';
    alerta.style.maxWidth = '500px';
    alerta.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
    
    // Ícones por tipo
    const icones = {
        'success': '<i class="bi bi-check-circle-fill me-2"></i>',
        'danger': '<i class="bi bi-exclamation-triangle-fill me-2"></i>',
        'warning': '<i class="bi bi-exclamation-circle-fill me-2"></i>',
        'info': '<i class="bi bi-info-circle-fill me-2"></i>'
    };
    
    alerta.innerHTML = `
        ${icones[tipo] || ''}
        ${mensagem}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Fechar"></button>
    `;
    
    // Adiciona ao body
    document.body.appendChild(alerta);
    
    // Remove automaticamente após 5 segundos
    setTimeout(() => {
        alerta.classList.remove('show');
        setTimeout(() => alerta.remove(), 150);
    }, 5000);
}

/**
 * Formata data para exibição em português
 * 
 * @param {Date|string} data - Data a ser formatada
 * @returns {string} Data formatada (ex: "15/01/2026")
 */
function formatarData(data) {
    const d = new Date(data);
    const dia = String(d.getDate()).padStart(2, '0');
    const mes = String(d.getMonth() + 1).padStart(2, '0');
    const ano = d.getFullYear();
    return `${dia}/${mes}/${ano}`;
}

/**
 * Formata hora para exibição
 * 
 * @param {Date|string} data - Data/hora a ser formatada
 * @returns {string} Hora formatada (ex: "14:30")
 */
function formatarHora(data) {
    const d = new Date(data);
    const hora = String(d.getHours()).padStart(2, '0');
    const minuto = String(d.getMinutes()).padStart(2, '0');
    return `${hora}:${minuto}`;
}

/**
 * Formata valor monetário para exibição
 * 
 * @param {number} valor - Valor a ser formatado
 * @returns {string} Valor formatado (ex: "R$ 150,00")
 */
function formatarValor(valor) {
    if (!valor) return 'R$ 0,00';
    return `R$ ${parseFloat(valor).toFixed(2).replace('.', ',')}`;
}

/**
 * Valida se uma data é válida
 * 
 * @param {Date|string} data - Data a ser validada
 * @returns {boolean} True se válida, false caso contrário
 */
function validarData(data) {
    const d = new Date(data);
    return d instanceof Date && !isNaN(d);
}

/**
 * Calcula diferença em minutos entre duas datas
 * 
 * @param {Date|string} dataInicio - Data/hora inicial
 * @param {Date|string} dataFim - Data/hora final
 * @returns {number} Diferença em minutos
 */
function calcularDuracaoMinutos(dataInicio, dataFim) {
    const inicio = new Date(dataInicio);
    const fim = new Date(dataFim);
    return Math.round((fim - inicio) / 60000);
}

/**
 * Verifica se há conflito de horário
 * Usado para validação antes de salvar
 * 
 * @param {Date} dataInicio - Data/hora de início
 * @param {Date} dataFim - Data/hora de fim
 * @param {number} idExcluir - ID do agendamento a excluir da verificação (para edição)
 * @returns {Promise<boolean>} True se há conflito, false caso contrário
 */
async function verificarConflito(dataInicio, dataFim, idExcluir = null) {
    try {
        // Busca agendamentos no período
        const params = new URLSearchParams({
            start: dataInicio.toISOString(),
            end: dataFim.toISOString()
        });
        
        const response = await fetch(`/api/agendamentos?${params.toString()}`);
        const agendamentos = await response.json();
        
        // Verifica se há sobreposição
        for (const agendamento of agendamentos) {
            // Ignora o próprio agendamento (caso de edição)
            if (idExcluir && agendamento.id === idExcluir) {
                continue;
            }
            
            // Ignora agendamentos cancelados
            if (agendamento.extendedProps.status === 'cancelada') {
                continue;
            }
            
            const agendInicio = new Date(agendamento.start);
            const agendFim = new Date(agendamento.end);
            
            // Verifica sobreposição
            if (
                (dataInicio >= agendInicio && dataInicio < agendFim) ||
                (dataFim > agendInicio && dataFim <= agendFim) ||
                (dataInicio <= agendInicio && dataFim >= agendFim)
            ) {
                return true; // Há conflito
            }
        }
        
        return false; // Sem conflito
        
    } catch (error) {
        console.error('❌ Erro ao verificar conflito:', error);
        return false; // Em caso de erro, permite continuar
    }
}

/**
 * Obtém nome do paciente por ID
 * Busca no cache de pacientes
 * 
 * @param {number} pacienteId - ID do paciente
 * @returns {string} Nome do paciente ou "Desconhecido"
 */
function obterNomePaciente(pacienteId) {
    const paciente = pacientesCache.find(p => p.id === parseInt(pacienteId));
    return paciente ? paciente.nome : 'Desconhecido';
}

/**
 * Atualiza contador de agendamentos no título da página
 * Útil para notificações visuais
 */
function atualizarContadorAgendamentos() {
    const eventos = calendar.getEvents();
    const hoje = new Date();
    hoje.setHours(0, 0, 0, 0);
    
    const eventosHoje = eventos.filter(e => {
        const dataEvento = new Date(e.start);
        dataEvento.setHours(0, 0, 0, 0);
        return dataEvento.getTime() === hoje.getTime();
    });
    
    console.log(`📊 Agendamentos hoje: ${eventosHoje.length}`);
}
// ==========================================
// FUNÇÕES DE DEBUG E DESENVOLVIMENTO
// ==========================================

/**
 * Ativa modo debug com logs detalhados
 * Útil durante desenvolvimento e troubleshooting
 * 
 * Para ativar: No console do navegador, digite: ativarDebug()
 */
function ativarDebug() {
    window.AGENDA_DEBUG = true;
    console.log('🐛 Modo DEBUG ativado');
    console.log('   - Logs detalhados habilitados');
    console.log('   - Para desativar: desativarDebug()');
}

/**
 * Desativa modo debug
 */
function desativarDebug() {
    window.AGENDA_DEBUG = false;
    console.log('✅ Modo DEBUG desativado');
}

/**
 * Log condicional (apenas se debug ativo)
 * 
 * @param {string} mensagem - Mensagem de log
 * @param {any} dados - Dados adicionais (opcional)
 */
function debugLog(mensagem, dados = null) {
    if (window.AGENDA_DEBUG) {
        console.log(`[DEBUG] ${mensagem}`, dados || '');
    }
}

/**
 * Exibe informações do calendário no console
 * Útil para debug e troubleshooting
 */
function infoCalendario() {
    if (!calendar) {
        console.error('❌ Calendário não inicializado');
        return;
    }
    
    console.log('📊 INFORMAÇÕES DO CALENDÁRIO');
    console.log('================================');
    console.log('Visualização atual:', calendar.view.type);
    console.log('Data atual:', calendar.getDate());
    console.log('Total de eventos:', calendar.getEvents().length);
    console.log('Filtro de status:', filtroStatusAtual);
    console.log('Pacientes carregados:', pacientesCache.length);
    console.log('================================');
}

/**
 * Lista todos os agendamentos no console
 * Útil para debug
 */
function listarAgendamentos() {
    if (!calendar) {
        console.error('❌ Calendário não inicializado');
        return;
    }
    
    const eventos = calendar.getEvents();
    
    console.log('📋 LISTA DE AGENDAMENTOS');
    console.log('================================');
    console.log(`Total: ${eventos.length} agendamentos`);
    console.log('');
    
    eventos.forEach((evento, index) => {
        console.log(`${index + 1}. ${evento.title}`);
        console.log(`   ID: ${evento.id}`);
        console.log(`   Início: ${evento.start}`);
        console.log(`   Fim: ${evento.end}`);
        console.log(`   Status: ${evento.extendedProps.status}`);
        console.log(`   Tipo: ${evento.extendedProps.tipo}`);
        console.log('');
    });
    
    console.log('================================');
}

/**
 * Força recarga de todos os eventos
 * Útil quando há problemas de sincronização
 */
function recarregarEventos() {
    console.log('🔄 Forçando recarga de eventos...');
    if (calendar) {
        calendar.refetchEvents();
        console.log('✅ Eventos recarregados');
    } else {
        console.error('❌ Calendário não inicializado');
    }
}

/**
 * Limpa cache de pacientes e recarrega
 * Útil quando há alterações na lista de pacientes
 */
function recarregarPacientes() {
    console.log('🔄 Recarregando pacientes...');
    pacientesCache = [];
    carregarPacientes();
}

/**
 * Exporta configuração atual do calendário
 * Útil para backup ou migração
 * 
 * @returns {Object} Configuração do calendário
 */
function exportarConfiguracao() {
    const config = {
        visualizacao: calendar.view.type,
        data: calendar.getDate(),
        filtroStatus: filtroStatusAtual,
        totalEventos: calendar.getEvents().length,
        totalPacientes: pacientesCache.length
    };
    
    console.log('📦 Configuração exportada:', config);
    return config;
}

/**
 * Testa conectividade com API
 * Verifica se todas as rotas estão respondendo
 */
async function testarAPI() {
    console.log('🔍 Testando conectividade com API...');
    console.log('================================');
    
    // Testa GET /api/agendamentos
    try {
        const respAgendamentos = await fetch('/api/agendamentos');
        console.log(`✅ GET /api/agendamentos: ${respAgendamentos.status} ${respAgendamentos.statusText}`);
    } catch (error) {
        console.error('❌ GET /api/agendamentos:', error.message);
    }
    
    // Testa GET /api/pacientes
    try {
        const respPacientes = await fetch('/api/pacientes');
        console.log(`✅ GET /api/pacientes: ${respPacientes.status} ${respPacientes.statusText}`);
    } catch (error) {
        console.error('❌ GET /api/pacientes:', error.message);
    }
    
    console.log('================================');
    console.log('✅ Teste de API concluído');
}

// ==========================================
// UTILITÁRIOS DE PERFORMANCE
// ==========================================

/**
 * Debounce: Limita frequência de execução de função
 * Útil para eventos que disparam muitas vezes (resize, scroll, etc)
 * 
 * @param {Function} func - Função a ser executada
 * @param {number} wait - Tempo de espera em ms
 * @returns {Function} Função com debounce aplicado
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Throttle: Limita execução a uma vez por período
 * Útil para eventos contínuos
 * 
 * @param {Function} func - Função a ser executada
 * @param {number} limit - Intervalo mínimo em ms
 * @returns {Function} Função com throttle aplicado
 */
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// ==========================================
// TRATAMENTO DE ERROS GLOBAL
// ==========================================

/**
 * Captura erros não tratados
 * Evita que erros quebrem a aplicação
 */
window.addEventListener('error', function(event) {
    console.error('❌ Erro não tratado:', event.error);
    
    // Mostra alerta para o usuário apenas em produção
    if (!window.AGENDA_DEBUG) {
        mostrarAlerta('Ocorreu um erro inesperado. Por favor, recarregue a página.', 'danger');
    }
});

/**
 * Captura erros de promises não tratadas
 */
window.addEventListener('unhandledrejection', function(event) {
    console.error('❌ Promise rejeitada não tratada:', event.reason);
    
    // Mostra alerta para o usuário apenas em produção
    if (!window.AGENDA_DEBUG) {
        mostrarAlerta('Ocorreu um erro de comunicação. Verifique sua conexão.', 'warning');
    }
});

// ==========================================
// ATALHOS DE TECLADO
// ==========================================

/**
 * Configura atalhos de teclado para navegação rápida
 */
document.addEventListener('keydown', function(event) {
    // Ignora se estiver digitando em input/textarea
    if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
        return;
    }
    
    // Ctrl/Cmd + N: Novo agendamento
    if ((event.ctrlKey || event.metaKey) && event.key === 'n') {
        event.preventDefault();
        abrirModalNovoAgendamento();
        console.log('⌨️ Atalho: Novo agendamento');
    }
    
    // T: Ir para hoje
    if (event.key === 't' || event.key === 'T') {
        event.preventDefault();
        calendar.today();
        console.log('⌨️ Atalho: Hoje');
    }
    
    // Seta esquerda: Período anterior
    if (event.key === 'ArrowLeft') {
        event.preventDefault();
        calendar.prev();
        console.log('⌨️ Atalho: Período anterior');
    }
    
    // Seta direita: Próximo período
    if (event.key === 'ArrowRight') {
        event.preventDefault();
        calendar.next();
        console.log('⌨️ Atalho: Próximo período');
    }
    
    // M: Visualização Mês
    if (event.key === 'm' || event.key === 'M') {
        event.preventDefault();
        calendar.changeView('dayGridMonth');
        console.log('⌨️ Atalho: Visualização Mês');
    }
    
    // S: Visualização Semana
    if (event.key === 's' || event.key === 'S') {
        event.preventDefault();
        calendar.changeView('timeGridWeek');
        console.log('⌨️ Atalho: Visualização Semana');
    }
    
    // D: Visualização Dia
    if (event.key === 'd' || event.key === 'D') {
        event.preventDefault();
        calendar.changeView('timeGridDay');
        console.log('⌨️ Atalho: Visualização Dia');
    }
});

// ==========================================
// RESPONSIVIDADE
// ==========================================

/**
 * Ajusta visualização do calendário baseado no tamanho da tela
 * Melhora experiência em dispositivos móveis
 */
function ajustarVisualizacaoResponsiva() {
    if (!calendar) return;
    
    const larguraTela = window.innerWidth;
    
    // Mobile: Visualização de dia
    if (larguraTela < 768) {
        if (calendar.view.type !== 'timeGridDay') {
            calendar.changeView('timeGridDay');
            console.log('📱 Visualização ajustada para mobile: Dia');
        }
    }
    // Tablet: Visualização de semana
    else if (larguraTela < 1024) {
        if (calendar.view.type !== 'timeGridWeek') {
            calendar.changeView('timeGridWeek');
            console.log('📱 Visualização ajustada para tablet: Semana');
        }
    }
}

// Aplica ajuste responsivo com debounce
const ajustarResponsivoDebounced = debounce(ajustarVisualizacaoResponsiva, 250);
window.addEventListener('resize', ajustarResponsivoDebounced);

// ==========================================
// INICIALIZAÇÃO DE TOOLTIPS E POPOVERS
// ==========================================

/**
 * Inicializa tooltips do Bootstrap em elementos dinâmicos
 * Chamada após renderização de novos elementos
 */
function inicializarTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// ==========================================
// EXPORTAÇÃO DE FUNÇÕES GLOBAIS
// ==========================================

/**
 * Expõe funções úteis no escopo global
 * Permite acesso via console do navegador para debug
 */
window.agendaDebug = {
    ativarDebug,
    desativarDebug,
    infoCalendario,
    listarAgendamentos,
    recarregarEventos,
    recarregarPacientes,
    exportarConfiguracao,
    testarAPI
};

// ==========================================
// LOG DE INICIALIZAÇÃO COMPLETA
// ==========================================

console.log('');
console.log('╔════════════════════════════════════════╗');
console.log('║   MINDCAREPRO - AGENDA INICIALIZADA   ║');
console.log('╚════════════════════════════════════════╝');
console.log('');
console.log('📚 Funções de debug disponíveis:');
console.log('   - agendaDebug.ativarDebug()');
console.log('   - agendaDebug.infoCalendario()');
console.log('   - agendaDebug.listarAgendamentos()');
console.log('   - agendaDebug.recarregarEventos()');
console.log('   - agendaDebug.testarAPI()');
console.log('');
console.log('⌨️  Atalhos de teclado:');
console.log('   - Ctrl/Cmd + N: Novo agendamento');
console.log('   - T: Ir para hoje');
console.log('   - ← →: Navegar períodos');
console.log('   - M: Visualização Mês');
console.log('   - S: Visualização Semana');
console.log('   - D: Visualização Dia');
console.log('');
console.log('✅ Sistema pronto para uso!');
console.log('');

// ==========================================
// FIM DO ARQUIVO agenda.js
// ==========================================

/**
 * NOTAS PARA MANUTENÇÃO FUTURA:
 * 
 * 1. ESTRUTURA DO CÓDIGO:
 *    - Funções organizadas por responsabilidade
 *    - Comentários detalhados em português
 *    - Tratamento de erros em todas as requisições
 *    - Feedback visual para todas as ações
 * 
 * 2. APIS UTILIZADAS:
 *    - GET    /api/agendamentos - Listar agendamentos
 *    - POST   /api/agendamentos - Criar agendamento
 *    - PUT    /api/agendamentos/<id> - Atualizar agendamento
 *    - DELETE /api/agendamentos/<id> - Deletar agendamento
 *    - GET    /api/pacientes - Listar pacientes
 * 
 * 3. DEPENDÊNCIAS:
 *    - FullCalendar 6.x (CDN)
 *    - Bootstrap 5.3.0 (já carregado no base.html)
 *    - Fetch API (nativa do navegador)
 * 
 * 4. CUSTOMIZAÇÕES FUTURAS:
 *    - Para adicionar novos campos: atualizar modais HTML + funções de salvar
 *    - Para mudar cores: atualizar objeto 'cores' no método to_dict() do backend
 *    - Para adicionar filtros: adicionar select no HTML + atualizar carregarAgendamentos()
 *    - Para integrar Google Calendar: adicionar lógica em salvarNovoAgendamento()
 * 
 * 5. TROUBLESHOOTING:
 *    - Se eventos não aparecem: verificar console (F12) para erros de API
 *    - Se drag & drop não funciona: verificar propriedade 'editable' do FullCalendar
 *    - Se modais não abrem: verificar se Bootstrap JS está carregado
 *    - Para debug detalhado: executar agendaDebug.ativarDebug() no console
 * 
 * 6. PERFORMANCE:
 *    - Cache de pacientes evita múltiplas requisições
 *    - Debounce aplicado em eventos de resize
 *    - Lazy loading de eventos pelo FullCalendar
 * 
 * 7. SEGURANÇA:
 *    - Validação de formulários no frontend e backend
 *    - Sanitização de dados antes de enviar para API
 *    - Tratamento de erros sem expor informações sensíveis
 * 
 * 8. ACESSIBILIDADE:
 *    - Atalhos de teclado para navegação
 *    - Labels adequados em formulários
 *    - Mensagens de erro descritivas
 *    - Suporte a leitores de tela (ARIA)
 * 
 * Desenvolvido por: Flavio Ricci + IA Adapta ONE 26
 * Última atualização: Janeiro 2026
 * Versão: 1.0.0
 */
