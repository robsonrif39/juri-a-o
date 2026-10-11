function acessar(pagina) {
    let url = '';
    switch(pagina) {
        case 'cadastro':
            url = '/cadastro';
            break;
        case 'consulta':
            url = '/consulta';
            break;
        case 'calendario':
            url = '/calendario';
            break;
        case 'lista':
            url = '/lista';
            break;
    }
    window.location.href = url;
}