# Blueprint permite organizar as rotas do perfil em um arquivo separado,
# sem substituir o main.py que contém o login, cadastro e dashboard.
from flask import Blueprint, render_template, request, redirect, url_for, session, flash

# Essas funções são do Werkzeug, usado junto com Flask para tratar senhas.
# generate_password_hash transforma a senha em um hash antes de salvar no banco.
# check_password_hash compara uma senha digitada com o hash que já está salvo.
from werkzeug.security import generate_password_hash, check_password_hash

# fdb é a biblioteca de conexão com banco de dados Firebird.
import fdb


# Todas as rotas deste arquivo terão o nome do Blueprint "perfil".
perfil_bp = Blueprint("perfil", __name__)


def conectar_banco():
    """
    Esta função é apenas um espaço reservado para integração.
    A equipe deve trocar o conteúdo pela função de conexão Firebird já usada
    no projeto principal. Ela não conecta enquanto estiver assim.
    """
    raise NotImplementedError(
        "Conecte esta função ao método conectar_banco() do projeto principal."
    )


# Rota GET: abre a página e busca os dados atuais do usuário.
@perfil_bp.route("/perfil", methods=["GET"])
def pagina_perfil():
    # A sessão identifica qual usuário fez login.
    # Se não existir ID na sessão, a pessoa ainda não está autenticada.
    if "id_usuario" not in session:
        flash("Faça login para acessar o perfil.")
        return redirect(url_for("login"))

    # Abre a conexão e cria um cursor, usado para executar SQL.
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        # O ponto de interrogação (?) é um parâmetro do SQL.
        # Passar o ID separadamente evita montar a consulta juntando texto do usuário.
        # Não buscamos nem alteramos a chave primária; ela serve apenas para localizar a conta.
        cursor.execute("""
            SELECT ID_USUARIO, NOME, EMAIL, ATIVO,
                   TENTATIVAS_LOGIN, BLOQUEADO
            FROM USUARIO
            WHERE ID_USUARIO = ?
        """, (session["id_usuario"],))

        # fetchone() retorna uma linha encontrada ou None se não houver usuário.
        linha = cursor.fetchone()

        if linha is None:
            # Se a conta não existe mais, limpamos o ID da sessão e pedimos novo login.
            session.pop("id_usuario", None)
            flash("Usuário não encontrado.")
            return redirect(url_for("login"))

        # Um dicionário associa nomes fáceis de ler aos valores retornados pelo banco.
        # O HTML usa, por exemplo, usuario.nome e usuario.email.
        usuario = {
            "id_usuario": linha[0],
            "nome": linha[1] or "",
            "email": linha[2] or "",
            "ativo": bool(linha[3]),
            "tentativas_login": linha[4] if linha[4] is not None else 0,
            "bloqueado": bool(linha[5]),
        }

        # Envia os dados encontrados para o arquivo HTML.
        return render_template("perfil.html", usuario=usuario)

    finally:
        # finally é executado mesmo se ocorrer um erro ou houver um return.
        # Isso ajuda a não deixar cursor e conexão abertos.
        cursor.close()
        conexao.close()


# Rota POST: recebe o formulário quando a pessoa clica em "Salvar dados".
@perfil_bp.route("/perfil/editar", methods=["POST"])
def editar_perfil():
    # Confere se o usuário está autenticado antes de permitir alterações.
    if "id_usuario" not in session:
        flash("Faça login para editar o perfil.")
        return redirect(url_for("login"))

    # O ID vem da sessão, não de um campo editável do formulário.
    # Assim, a pessoa não escolhe qual conta será alterada por meio do HTML.
    id_usuario = session["id_usuario"]

    # request.form lê os valores enviados pelo formulário HTML.
    # strip() remove espaços extras no começo e no fim de nome e e-mail.
    nome = request.form.get("nome", "").strip()
    email = request.form.get("email", "").strip()

    # Os selects enviam "1" ou "0"; convertemos para valores booleanos.
    ativo = request.form.get("ativo") == "1"
    bloqueado = request.form.get("bloqueado") == "1"

    # O campo numérico chega como texto, então int() o converte para inteiro.
    tentativas = request.form.get("tentativas_login", "0")

    # A senha atual é usada para confirmar a identidade antes de trocar a senha.
    senha_atual = request.form.get("senha_atual", "")
    nova_senha = request.form.get("nova_senha", "")

    # Verificação básica: nome e e-mail não podem ficar vazios.
    if not nome or not email:
        flash("Preencha o nome e o e-mail.")
        return redirect(url_for("perfil.pagina_perfil"))

    # try/except captura erro caso o campo de tentativas não seja um número válido.
    try:
        tentativas = int(tentativas)
        if tentativas < 0:
            raise ValueError
    except ValueError:
        flash("O número de tentativas precisa ser zero ou maior.")
        return redirect(url_for("perfil.pagina_perfil"))

    # A conexão real será configurada pela equipe na integração.
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        # Primeiro, lemos o hash da senha atual para verificar a senha e o histórico.
        cursor.execute("""
            SELECT SENHA
            FROM USUARIO
            WHERE ID_USUARIO = ?
        """, (id_usuario,))
        linha = cursor.fetchone()

        if linha is None:
            flash("Usuário não encontrado.")
            return redirect(url_for("login"))

        senha_salva = linha[0]
        senha_final = senha_salva

        # Se nova_senha estiver vazia, a senha não é alterada.
        # Se estiver preenchida, fazemos as verificações abaixo.
        if nova_senha:
            if not senha_atual:
                flash("Informe a senha atual para definir uma nova senha.")
                return redirect(url_for("perfil.pagina_perfil"))

            # check_password_hash verifica a senha digitada contra o hash armazenado.
            if not senha_salva or not check_password_hash(senha_salva, senha_atual):
                flash("A senha atual está incorreta.")
                return redirect(url_for("perfil.pagina_perfil"))

            # FIRST 3 é a forma do Firebird para limitar a consulta às três linhas.
            # Ordenamos da mais recente para a mais antiga.
            cursor.execute("""
                SELECT FIRST 3 SENHA
                FROM HISTORICO_SENHA
                WHERE ID_USUARIO = ?
                ORDER BY DATA_ALTERACAO DESC, ID_HISTORICO_SENHA DESC
            """, (id_usuario,))
            historico = cursor.fetchall()

            # A senha atual também não pode ser reutilizada.
            # Juntamos o hash atual com os hashes retornados do histórico.
            senhas_bloqueadas = [senha_salva] + [
                item[0] for item in historico if item[0]
            ]

            # Cada hash é comparado à nova senha digitada.
            for hash_antigo in senhas_bloqueadas:
                if check_password_hash(hash_antigo, nova_senha):
                    flash("Não é permitido reutilizar a senha atual ou uma das últimas 3 senhas.")
                    return redirect(url_for("perfil.pagina_perfil"))

            # Antes de trocar, guardamos a senha antiga no histórico.
            # CURRENT_TIMESTAMP é um valor do Firebird com data e hora atuais.
            cursor.execute("""
                INSERT INTO HISTORICO_SENHA
                    (SENHA, ID_USUARIO, DATA_ALTERACAO)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (senha_salva, id_usuario))

            # A nova senha é transformada em hash antes de ser salva.
            # Não guardamos a nova senha em texto puro no banco.
            senha_final = generate_password_hash(nova_senha)

        # Atualiza todos os campos incluídos nesta etapa, exceto ID_USUARIO.
        # TIPO foi deixado de fora porque a parte de usuário/administrador será feita depois.
        cursor.execute("""
            UPDATE USUARIO
            SET NOME = ?, EMAIL = ?, SENHA = ?, ATIVO = ?,
                TENTATIVAS_LOGIN = ?, BLOQUEADO = ?
            WHERE ID_USUARIO = ?
        """, (
            nome, email, senha_final, ativo, tentativas, bloqueado, id_usuario
        ))

        # commit() confirma as alterações no banco.
        conexao.commit()
        flash("Perfil atualizado com sucesso!")

    except fdb.IntegrityError:
        # rollback() desfaz alterações da operação se houver erro de integridade,
        # por exemplo, e-mail duplicado quando EMAIL tem uma restrição UNIQUE.
        conexao.rollback()
        flash("Este e-mail já está cadastrado.")

    except NotImplementedError:
        # Mantém visível o erro do espaço reservado de conexão enquanto não integrado.
        conexao.rollback()
        raise

    except Exception:
        # Captura outros erros para não exibir detalhes técnicos ao usuário da página.
        # Durante a integração, a equipe pode consultar o terminal para investigar.
        conexao.rollback()
        flash("Não foi possível atualizar o perfil. Confira a conexão e os dados do banco.")

    finally:
        # Fecha os recursos abertos, mesmo quando acontece algum erro.
        cursor.close()
        conexao.close()

    # Redireciona para a página depois de processar o formulário.
    return redirect(url_for("perfil.pagina_perfil"))
