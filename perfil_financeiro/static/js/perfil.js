// Busca o formulário pelo ID que foi definido no HTML.
const formulario = document.getElementById("form-perfil");

// addEventListener executa esta função quando a pessoa tenta enviar o formulário.
formulario.addEventListener("submit", function (evento) {
    // Lê o que foi digitado nos campos de senha.
    const senhaAtual = document.getElementById("senha_atual").value;
    const novaSenha = document.getElementById("nova_senha").value;

    // Se uma nova senha foi informada, a senha atual também é obrigatória.
    if (novaSenha !== "" && senhaAtual === "") {
        // preventDefault cancela o envio normal do formulário.
        evento.preventDefault();
        alert("Informe sua senha atual para alterar a senha.");
        return;
    }

    // Evita que a pessoa preencha apenas a senha atual sem uma nova senha.
    if (novaSenha === "" && senhaAtual !== "") {
        evento.preventDefault();
        alert("Preencha a nova senha ou deixe os dois campos vazios.");
    }
});

// Esta validação melhora a experiência, mas a verificação de segurança real
// acontece no Python, no servidor. O JavaScript sozinho não protege o banco.
