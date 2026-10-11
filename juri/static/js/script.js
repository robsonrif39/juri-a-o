// Simulação de dados de processos
const processos = [
    { numero: '123456789', status: 'Em Andamento', advogado: 'Dr. João Silva' },
    { numero: '987654321', status: 'Concluído', advogado: 'Dra. Maria Oliveira' },
    { numero: '456789123', status: 'Em Andamento', advogado: 'Dr. Carlos Souza' }
];

// Exibir os processos encontrados
function exibirProcessos(lista) {
    const listaElement = document.getElementById('processos-lista');
    listaElement.innerHTML = ''; // Limpar resultados anteriores
    lista.forEach(processo => {
        const div = document.createElement('div');
        div.classList.add('processo');
        div.innerHTML = `
            <p><strong>Número do Processo:</strong> ${processo.numero}</p>
            <p><strong>Status:</strong> ${processo.status}</p>
            <p><strong>Advogado:</strong> ${processo.advogado}</p>
        `;
        listaElement.appendChild(div);
    });
}

// Evento para o formulário de pesquisa
document.getElementById('pesquisa-form').addEventListener('submit', function(event) {
    event.preventDefault();
    const oab = document.getElementById('oab').value;

    // Simulação de dados de processos
    const processos = [
        { numero: '123456789', status: 'Em Andamento', advogado: 'Dr. João Silva', prazo: 10 },
        { numero: '987654321', status: 'Concluído', advogado: 'Dra. Maria Oliveira', prazo: 30 },
        { numero: '456789123', status: 'Em Andamento', advogado: 'Dr. Carlos Souza', prazo: 5 }
    ];

    // Filtrar processos pela OAB (simulação)
    const processosFiltrados = processos.filter(processo => processo.numero.includes(oab));

    // Exibir os processos encontrados
    const lista = document.getElementById('processos-lista');
    lista.innerHTML = ''; // Limpar resultados anteriores
    if (processosFiltrados.length > 0) {
        processosFiltrados.forEach(processo => {
            const div = document.createElement('div');
            div.classList.add('processo');
            div.innerHTML = `
                <p><strong>Número do Processo:</strong> ${processo.numero}</p>
                <p><strong>Status:</strong> ${processo.status}</p>
                <p><strong>Advogado:</strong> ${processo.advogado}</p>
                <p><strong>Prazo:</strong> ${processo.prazo} dias</p>
            `;
            lista.appendChild(div);
        });
    } else {
        lista.innerHTML = '<p>Nenhum processo encontrado para esta OAB.</p>';
    }
});

// Registrar prazo e atualizar lista de acompanhamento
document.getElementById('registrar-prazo-btn').addEventListener('click', function() {
    const prazoInput = document.getElementById('prazo-input').value;
    const acompanhamentoLista = document.getElementById('acompanhamento-lista');

    if (!prazoInput || isNaN(prazoInput) || prazoInput <= 0) {
        alert('Por favor, insira um prazo válido.');
        return;
    }

    // Adicionar o prazo e calcular o status
    const prazo = parseInt(prazoInput, 10);
    let statusPrazo = '';
    if (prazo <= 10) {
        statusPrazo = 'Dentro do prazo';
    } else if (prazo <= 30) {
        statusPrazo = 'Vencendo';
    } else {
        statusPrazo = 'Prazo vencido';
    }

    // Criar um item na lista de acompanhamento
    const div = document.createElement('div');
    div.classList.add('acompanhamento-item');
    div.innerHTML = `
        <p><strong>Prazo:</strong> ${prazo} dias</p>
        <p><strong>Status:</strong> ${statusPrazo}</p>
    `;
    acompanhamentoLista.appendChild(div);

    // Limpar o campo de entrada
    document.getElementById('prazo-input').value = '';
});
document.querySelectorAll('.tab-link').forEach(link => {
    link.addEventListener('click', function(event) {
        event.preventDefault();
        document.querySelectorAll('.tab-link').forEach(link => link.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
        document.getElementById(this.dataset.tab).classList.add('active');
        this.classList.add('active');
    });
});

document.getElementById('consultaForm').addEventListener('submit', function(event) {
    event.preventDefault();
    const oab = document.getElementById('oab').value;

    // Simulação de consulta
    const movimentacao = 'Última movimentação: Audiência realizada em 05/05/2025';
    const prazo = document.getElementById('prazoSelect').value;

    document.getElementById('movimentacao').textContent = movimentacao;
    document.getElementById('prazo').textContent = `Prazo do processo: ${prazo} dias`;

    // Alerta de prazo vencendo
    const alertaPrazo = document.getElementById('alertaPrazo');
    if (prazo <= 5) {
        alertaPrazo.textContent = 'Alerta: Prazo vencendo em breve!';
    } else {
        alertaPrazo.textContent = '';
    }
});

document.getElementById('calendarioForm').addEventListener('submit', function(event) {
    event.preventDefault();
    const cliente = document.getElementById('cliente').value;
    const valor = document.getElementById('valor').value
	
	document.querySelectorAll('.tab-link').forEach(link => {
    link.addEventListener('click', function(event) {
        event.preventDefault();
        document.querySelectorAll('.tab-link').forEach(link => link.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
        document.getElementById(this.dataset.tab).classList.add('active');
        this.classList.add('active');
    });
});

// Adicionando clientes à lista
const clientes = [
    { nome: 'João Silva', cpf: '123.456.789-00', endereco: 'Rua A, 123' },
    { nome: 'Maria Oliveira', cpf: '987.654.321-00', endereco: 'Rua B, 456' },
    { nome: 'Carlos Souza', cpf: '456.789.123-00', endereco: 'Rua C, 789' }
];

const listaClientes = document.getElementById('clientes');
clientes.forEach(cliente => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${cliente.nome}</td><td>${cliente.cpf}</td><td>${cliente.endereco}</td>`;
    listaClientes.appendChild(tr);
});

document.getElementById('pesquisaForm').addEventListener('submit', function(event) {
    event.preventDefault();
    const pesquisa = document.getElementById('pesquisa').value.toLowerCase();
    const resultados = clientes.filter(cliente => cliente.nome.toLowerCase().includes(pesquisa) || cliente.cpf.includes(pesquisa));
    
    listaClientes.innerHTML = '';
    resultados.forEach(cliente => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${cliente.nome}</td><td>${cliente.cpf}</td><td>${cliente.endereco}</td>`;
        listaClientes.appendChild(tr);
    });

    if (resultados.length === 0) {
        listaClientes.innerHTML = '<tr><td colspan="3">Nenhum cliente encontrado</td></tr>';
    }
});

document.getElementById('consultaForm').addEventListener('submit', function(event) {
    event.preventDefault();
    const oab = document.getElementById('oab').value;

    // Simulação de consulta
    const movimentacao = 'Última movimentação: Audiência realizada em 05/05/2025';
    const prazo = document.getElementById('prazoSelect').value;

    document.getElementById('movimentacao').textContent = movimentacao;
    document.getElementById('prazo').textContent = `Prazo do processo: ${prazo} dias`;

    // Alerta de prazo vencendo
    const alertaPrazo = document.getElementById('alertaPrazo');
    if (prazo <= 5) {
        alertaPrazo.textContent = 'Alerta: Prazo vencendo em breve!';
    } else {
        alertaPrazo.textContent = '';
    }
});

document.getElementById('calendarioForm').addEventListener('submit', function(event) {
    event.preventDefault();
    const cliente = document.getElementById('cliente').value;
    const valor = document.getElementById('valor').value;

    const dia = document.createElement('div');
    dia.className = 'calendar-day';
    dia.textContent = `Cliente: ${cliente}\nValor: R$ ${valor}`;
    document.getElementById('calendario').appendChild(dia);
});
// Função para exibir clientes na tabela
        function exibirClientes(lista) {
            const tbody = document.getElementById("clientes");
            tbody.innerHTML = "";

            lista.forEach(cliente => {
                const linha = document.createElement("tr");
                linha.innerHTML = `
                    <td>${cliente.nome}</td>
                    <td>${cliente.cpf}</td>
                    <td>${cliente.endereco}</td>
                `;
                tbody.appendChild(linha);
            });
        }

        // Cadastro de cliente
        document.getElementById("cadastroForm").addEventListener("submit", function (event) {
            event.preventDefault();

            const nome = document.getElementById("nome").value;
            const cpf = document.getElementById("cpf").value;
            const tipoCaso = document.getElementById("tipoCaso").value;

            alert(`Cliente cadastrado com sucesso!\nNome: ${nome}\nCPF: ${cpf}\nTipo de Caso: ${tipoCaso}`);
            
            // Aqui você pode adicionar a lógica para salvar os dados no backend ou localStorage
        });

        // Pesquisa
        document.getElementById("pesquisaForm").addEventListener("submit", function (e) {
            e.preventDefault();
            const termo = document.getElementById("pesquisa").value.toLowerCase();
            const clientes = JSON.parse(localStorage.getItem("clientes")) || [];

            const filtrados = clientes.filter(cliente =>
                cliente.nome.toLowerCase().includes(termo) ||
                cliente.cpf.includes(termo) ||
                cliente.endereco.toLowerCase().includes(termo)
            );

            exibirClientes(filtrados);
        });

        // Carregar lista ao iniciar
        window.addEventListener("DOMContentLoaded", () => {
            const clientes = JSON.parse(localStorage.getItem("clientes")) || [];
            exibirClientes(clientes);
        });
        const monthNames = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
const alerts = {};  // { '2025-05-08': 'Cobrança...' }

let current = new Date();

function renderCalendar() {
    const calendar = document.getElementById('calendar');
    const monthYear = document.getElementById('monthYear');
    calendar.innerHTML = "";

    const year = current.getFullYear();
    const month = current.getMonth();
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    monthYear.textContent = `${monthNames[month]} ${year}`;

    const weekdays = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];
    weekdays.forEach(day => {
        const div = document.createElement('div');
        div.className = 'weekdays';
        div.textContent = day;
        calendar.appendChild(div);
    });

    for (let i = 0; i < firstDay; i++) {
        const empty = document.createElement('div');
        calendar.appendChild(empty);
    }

    for (let day = 1; day <= daysInMonth; day++) {
        const dateKey = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        const div = document.createElement('div');
        div.className = 'day';
        if (alerts[dateKey]) div.classList.add('alert');

        div.textContent = day;
        div.onclick = () => addAlert(dateKey);
        calendar.appendChild(div);
    }
}

function changeMonth(offset) {
    current.setMonth(current.getMonth() + offset);
    renderCalendar();
}

function addAlert(date) {
    const msg = prompt(`Adicionar alerta para ${date}:`, alerts[date] || '');
    if (msg) {
        alerts[date] = msg;
    } else {
        delete alerts[date];
    }
    renderCalendar();
}

// Função para exibir os avisos abaixo do calendário
function renderAvisos() {
    const avisosDiv = document.getElementById('avisos-lista');
    avisosDiv.innerHTML = '';
    const chaves = Object.keys(alerts).sort();
    if (chaves.length === 0) {
        avisosDiv.innerHTML = '<p>Nenhum aviso registrado.</p>';
        return;
    }
    const ul = document.createElement('ul');
    chaves.forEach(data => {
        const li = document.createElement('li');
        li.textContent = `${data}: ${alerts[data]}`;
        ul.appendChild(li);
    });
    avisosDiv.appendChild(ul);
}

// Captura o submit do formulário e registra os avisos recorrentes
document.getElementById('calendarioForm').addEventListener('submit', function(e) {
    e.preventDefault();
    const cliente = document.getElementById('cliente').value;
    const valor = document.getElementById('valor').value;
    const dataInicial = document.getElementById('data').value;
    const parcelas = parseInt(document.getElementById('parcelas').value);

    if (!dataInicial || parcelas < 1) return;

    let data = new Date(dataInicial);
    for (let i = 0; i < parcelas; i++) {
        const ano = data.getFullYear();
        const mes = String(data.getMonth() + 1).padStart(2, '0');
        const dia = String(data.getDate()).padStart(2, '0');
        const dateKey = `${ano}-${mes}-${dia}`;
        alerts[dateKey] = `Cobrança ${i+1}/${parcelas} - ${cliente} - R$ ${valor}`;
        // Avança 1 mês
        data.setMonth(data.getMonth() + 1);
    }
    renderCalendar();
    this.reset();
});

renderCalendar();

// Exemplo de proteção para formulário de cadastro
const cadastroForm = document.getElementById("cadastroForm");
if (cadastroForm) {
    cadastroForm.addEventListener("submit", function (event) {
        event.preventDefault();
        const nome = document.getElementById("nome").value;
        const cpf = document.getElementById("cpf").value;
        const tipoCaso = document.getElementById("tipoCaso").value;
        alert(`Cliente cadastrado com sucesso!\nNome: ${nome}\nCPF: ${cpf}\nTipo de Caso: ${tipoCaso}`);
        // Aqui você pode adicionar a lógica para salvar os dados no backend ou localStorage
    });
}

// Exemplo de proteção para formulário de pesquisa
const pesquisaForm = document.getElementById("pesquisaForm");
if (pesquisaForm) {
    pesquisaForm.addEventListener("submit", function (e) {
        e.preventDefault();
        const termo = document.getElementById("pesquisa").value.toLowerCase();
        const clientes = JSON.parse(localStorage.getItem("clientes")) || [];

        const filtrados = clientes.filter(cliente =>
            cliente.nome.toLowerCase().includes(termo) ||
            cliente.cpf.includes(termo) ||
            cliente.endereco.toLowerCase().includes(termo)
        );

        exibirClientes(filtrados);
    });
}

// Repita para outros elementos conforme necessário
function renderAvisos() {
    const avisosDiv = document.getElementById('avisos-lista');
    avisosDiv.innerHTML = '';
    const chaves = Object.keys(alerts).sort();
    if (chaves.length === 0) {
        avisosDiv.innerHTML = '<p>Nenhum aviso registrado.</p>';
        return;
    }
    const ul = document.createElement('ul');
    chaves.forEach(data => {
        const li = document.createElement('li');
        li.textContent = `${data}: ${alerts[data]}`;
        ul.appendChild(li);
    });
    avisosDiv.appendChild(ul);
}
# Dispara a consulta assíncrona
fetch('/consulta_oab_async', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({oab: oab})
})
.then(resp => resp.json())
.then(data => {
    # Aguarda alguns segundos e busca o resultado pronto
    setTimeout(() => {
        fetch(`/consulta_resultado_oab/${oab}`)
            .then(resp => resp.json())
            .then(processos => {
                # ...exibe os processos como já faz...
            });
    }, 10000); # aguarda 10 segundos (ajuste conforme o tempo do scraping)
});
