/**
 * MindCarePro - Correção do Menu Lateral
 * 
 * Este script corrige o comportamento dos links do menu lateral,
 * garantindo que todos os cliques funcionem corretamente em todas as páginas.
 */

console.log('🔧 [Menu Fix] Carregando script de correção do menu...');

document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ [Menu Fix] DOM carregado, iniciando correções...');
    
    // Seleciona todos os links do menu
    const menuLinks = document.querySelectorAll('.menu-item');
    console.log(`📋 [Menu Fix] Encontrados ${menuLinks.length} itens de menu`);
    
    // Para cada link do menu
    menuLinks.forEach(function(link, index) {
        const linkText = link.textContent.trim();
        const linkUrl = link.getAttribute('href');
        
        console.log(`🔗 [Menu Fix] Configurando link ${index + 1}: "${linkText}" → ${linkUrl}`);
        
        // Remove todos os event listeners anteriores clonando o elemento
        const novoLink = link.cloneNode(true);
        link.parentNode.replaceChild(novoLink, link);
        
        // Adiciona novo event listener limpo
        novoLink.addEventListener('click', function(evento) {
            // Previne comportamento padrão
            evento.preventDefault();
            evento.stopPropagation();
            
            const url = this.getAttribute('href');
            const texto = this.textContent.trim();
            
            console.log(`✅ [Menu Fix] Clique detectado em: "${texto}"`);
            console.log(`🔗 [Menu Fix] Redirecionando para: ${url}`);
            
            // Redireciona para a URL
            window.location.href = url;
        });
        
        console.log(`✔️ [Menu Fix] Link "${linkText}" configurado com sucesso`);
    });
    
    console.log('✅ [Menu Fix] Todos os links do menu foram configurados com sucesso!');
    console.log('📌 [Menu Fix] Sistema pronto para uso');
});

// Log adicional para debug
console.log('📄 [Menu Fix] Script carregado completamente');
