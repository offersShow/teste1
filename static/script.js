function escapeHTML(str) {
  return str.replace(/[&<>"'`=\/]/g, function(s) {
    return ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
      "/": "&#x2F;",
      "`": "&#x60;",
      "=": "&#x3D;"
    })[s];
  });
}

document.getElementById("meuBotao").addEventListener("click", buscar);
document.getElementById("meuBotao2").addEventListener("click", iniciarPesquisa);


function iniciarPesquisa() {
  const termo = document.getElementById("termo-inicial").value.trim();
  if (!termo) return;

  // Preenche o campo principal e inicia a busca
  document.getElementById("termo").value = termo;
  sessionStorage.setItem("welcomeShown", "true");

  fecharModal();
  buscar(); // chama a função padrão
}

function fecharModal() {
  const modal = document.getElementById("welcome-modal");
  if (modal) modal.style.display = "none";
  document.body.classList.remove("modal-open");
}

document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("welcome-modal");

  if (!sessionStorage.getItem("welcomeShown")) {
    modal.style.display = "flex";
    document.body.classList.add("modal-open");
  } else {
    fecharModal(); // 🔒 garante que modal não bloqueie scroll
  }
});


// Função que dispara a busca via AJAX
function buscar() {
  const termo = document.getElementById("termo").value.trim();
  if (!termo) return;

  const container = document.getElementById("resultados");
  container.innerHTML = "<p class='loading'>Buscando...</p>";

  fetch('/api/buscar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ termo })
  })
  .then(response => response.json())
  .then(dados => {
    container.innerHTML = "";

    if (!dados.length) {
      container.innerHTML = "<p class='no-results'>Nenhum produto encontrado.</p>";
      return;
    }

    // Criar o containerResult
    const containerResult = document.createElement("div");
    containerResult.id = "containerResult";

    const titulo = document.createElement("h2");
    titulo.className = "titulo-resultados";
    titulo.textContent = `Resultados para: "${termo}"`;
    containerResult.appendChild(titulo);

    const wrapper = document.createElement("div");
    wrapper.className = "results-wrapper";

    const inner = document.createElement("div");
    inner.className = "results-container";


    // Seta de instrução
    const scrollHint = document.createElement("div");
    scrollHint.className = "scroll-hint";
    scrollHint.id = "scroll-hint";
    scrollHint.innerText = "⬅ Arraste para ver mais";
    wrapper.appendChild(scrollHint);

    const row = document.createElement("div");
    row.className = "results-container";


    dados.forEach(p => {
      
      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `
        <img src="${p.imagem}" alt="${p.nome}">
        <div class="card-content">
          <h2 title="${p.nome}">${p.nome}</h2>
          <p>R$ ${p.preco}</p>
          <a href="${p.link}" target="_blank">Ver na Amazon</a>
        </div>
      `;
      card.setAttribute('data-nome', p.nome);
      card.setAttribute('data-preco', p.preco);
      card.setAttribute('data-img', p.imagem);
      card.setAttribute('data-link', p.link);
      inner.appendChild(card);
    });

    wrapper.appendChild(inner);
    containerResult.appendChild(wrapper);
    container.appendChild(containerResult);

    // Scroll para o topo dos resultados
    containerResult.scrollIntoView({ behavior: "smooth", block: "start" });

    wrapper.addEventListener("scroll", () => {
    if (wrapper.scrollLeft > 30) {
      scrollHint.style.opacity = 0;
      setTimeout(() => scrollHint.remove(), 300);
    }
  })

    // Inicializa drag scroll
    initDragScroll(wrapper);
  })
  .catch(err => {
    console.error(err);
    container.innerHTML = "<p class='no-results'>Erro ao buscar produtos.</p>";
  });

}

// Lógica de arrastar para scroll horizontal
function initDragScroll(slider) {
  let isDown = false;
  let startX;
  let scrollLeft;

  slider.addEventListener('mousedown', e => {
    isDown = true;
    slider.classList.add('active');
    startX = e.pageX - slider.offsetLeft;
    scrollLeft = slider.scrollLeft;
  });
  slider.addEventListener('mouseleave', () => {
    isDown = false;
    slider.classList.remove('active');
  });
  slider.addEventListener('mouseup', () => {
    isDown = false;
    slider.classList.remove('active');
  });
  slider.addEventListener('mousemove', e => {
    if (!isDown) return;
    e.preventDefault();
    const x = e.pageX - slider.offsetLeft;
    const walk = (x - startX) * 2;
    slider.scrollLeft = scrollLeft - walk;
  });

  // Touch support
  slider.addEventListener('touchstart', e => {
    isDown = true;
    startX = e.touches[0].pageX - slider.offsetLeft;
    scrollLeft = slider.scrollLeft;
  });
  slider.addEventListener('touchend', () => {
    isDown = false;
  });
  slider.addEventListener('touchmove', e => {
    if (!isDown) return;
    const x = e.touches[0].pageX - slider.offsetLeft;
    const walk = (x - startX) * 2;
    slider.scrollLeft = scrollLeft - walk;
  });
}


// Permite acionar a busca também ao pressionar Enter
document.addEventListener("DOMContentLoaded", () => {
  // Requisição para obter a última busca via sessão
  fetch("/ultima_busca")
    .then(res => res.json())
    .then(({ termo, dados }) => {
      if (!termo || !dados || !dados.length) return;

      document.getElementById("termo").value = termo;
      renderizarResultados(termo, dados);  // usa a mesma função do fetch
    });
  const input = document.getElementById("termo");

    // Reanexar o drag scroll e eventos de rolagem
    const wrapper = document.querySelector(".results-wrapper");
    if (wrapper) {
      initDragScroll(wrapper);
      wrapper.addEventListener("scroll", () => {
        const hint = document.getElementById("scroll-hint");
        if (hint && wrapper.scrollLeft > 30) {
          hint.style.opacity = 0;
          setTimeout(() => hint.remove(), 300);
        }
      });
  }

  // placeholder digitando
  digitarPlaceholder();

  // Enter = buscar
  input.addEventListener("keyup", e => {
    if (e.key === "Enter") buscar();
  });
});
// função reutilizavel
function renderizarResultados(termo, dados) {
  const container = document.getElementById("resultados");
  container.innerHTML = "";

  const containerResult = document.createElement("div");
  containerResult.id = "containerResult";

  const titulo = document.createElement("h2");
  titulo.className = "titulo-resultados";
  titulo.textContent = `Resultados para: "${termo}"`;
  containerResult.appendChild(titulo);

  const wrapper = document.createElement("div");
  wrapper.className = "results-wrapper";

  const inner = document.createElement("div");
  inner.className = "results-container";

  const scrollHint = document.createElement("div");
  scrollHint.className = "scroll-hint";
  scrollHint.id = "scroll-hint";
  scrollHint.innerText = "⬅ Arraste para ver mais";
  wrapper.appendChild(scrollHint);

  dados.forEach(p => {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <img src="${p.imagem}" alt="${p.nome}">
      <div class="card-content">
        <h2 title="${p.nome}">${p.nome}</h2>
        <p>R$ ${p.preco || 'Preço indisponível'}</p>
        <a href="${p.link}" target="_blank">Ver na Amazon</a>
      </div>
    `;
    card.setAttribute('data-nome', p.nome);
    card.setAttribute('data-preco', p.preco);
    card.setAttribute('data-img', p.imagem);
    card.setAttribute('data-link', p.link);
    inner.appendChild(card);
  });

  wrapper.appendChild(inner);
  containerResult.appendChild(wrapper);
  container.appendChild(containerResult);

  containerResult.scrollIntoView({ behavior: "smooth", block: "start" });

  wrapper.addEventListener("scroll", () => {
    if (wrapper.scrollLeft > 30) {
      scrollHint.style.opacity = 0;
      setTimeout(() => scrollHint.remove(), 300);
    }
  });

  initDragScroll(wrapper);
}
// função acima reutilizavel

const frases = [
      "notebook gamer",
      "celular barato",
      "ssd 1TB",
      "fone bluetooth",
      "monitor ultrawide"
    ];

    let fraseIndex = 0;
    let charIndex = 0;
    let currentPlaceholder = "";
    const input = document.getElementById("termo");

    function digitarPlaceholder() {
      if (charIndex < frases[fraseIndex].length) {
        currentPlaceholder += frases[fraseIndex][charIndex++];
        input.setAttribute("placeholder", currentPlaceholder);
        setTimeout(digitarPlaceholder, 100);
      } else {
        setTimeout(() => apagarPlaceholder(), 1500);
      }
    }

    function apagarPlaceholder() {
      if (charIndex > 0) {
        currentPlaceholder = currentPlaceholder.slice(0, --charIndex);
        input.setAttribute("placeholder", currentPlaceholder);
        setTimeout(apagarPlaceholder, 50);
      } else {
        fraseIndex = (fraseIndex + 1) % frases.length;
        setTimeout(digitarPlaceholder, 200);
      }
    }

    document.addEventListener("DOMContentLoaded", () => {
      digitarPlaceholder();
    });


    // Esconde header ao rolar para baixo, mostra ao rolar para cima
    let lastScroll = 0;
    const header = document.getElementById('site-header');
    window.addEventListener('scroll', () => {
      const current = window.pageYOffset;
      if (current > lastScroll && current > 100) {
        // scroll down
        header.classList.add('header--hidden');
      } else {
        // scroll up
        header.classList.remove('header--hidden');
      }
      lastScroll = current;
    });



document.addEventListener("DOMContentLoaded", () => {
  fetch("/promocoes")
    .then(res => res.json())
    .then(promo_cache => {
      const categoriasDiv = document.getElementById("area-categorias");
      const produtosDiv = document.getElementById("area-produtos");

      Object.keys(promo_cache).forEach((categoria, index) => {
        const btn = document.createElement("button");
        btn.className = "botao-categoria";
        btn.textContent = categoria;

        btn.addEventListener("click", () => {
          document.querySelectorAll(".botao-categoria").forEach(b => b.classList.remove("ativo"));
          // Adiciona a classe no botão clicado
          btn.classList.add("ativo");
          // Limpa e mostra produtos da categoria clicada
          produtosDiv.innerHTML = "";
          promo_cache[categoria].forEach(p => {
            const card = document.createElement("div");
            card.className = "card";
            card.innerHTML = `
              <img src="${p.imagem}" alt="${p.nome}">
              <div class="card-content">
                <h2>${p.nome}</h2>
                <p>${p.preco ? `R$ ${p.preco}` : "Preço indisponível"}</p>
                <a href="${p.link}" target="_blank">Ver na Amazon</a>
              </div>
            `;
            card.setAttribute('data-nome', p.nome);
            card.setAttribute('data-preco', p.preco);
            card.setAttribute('data-img', p.imagem);
            card.setAttribute('data-link', p.link);
            produtosDiv.appendChild(card);
          });
        });

        categoriasDiv.appendChild(btn);

        // Opcional: exibe a primeira categoria automaticamente
        if (index === 0) btn.click();
      });
    });
});

document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('modal');
  const modalImg = document.getElementById('modal-imagem');
  const modalNome = document.getElementById('modal-nome');
  const modalPreco = document.getElementById('modal-preco');
  const modalLink = document.getElementById('modal-link');
  const closeBtn = document.querySelector('.modal .close');

  // EVENTO GLOBAL para elementos futuros
  document.body.addEventListener('click', e => {
    const card = e.target.closest('.card');
    if (!card) return;

    modal.style.display = 'flex';
    modalImg.src = card.dataset.img;
    modalNome.textContent = card.dataset.nome;
    modalPreco.textContent = `Preço: R$ ${card.dataset.preco}`;
    modalLink.href = card.dataset.link;
  });

  closeBtn.onclick = () => {
    modal.style.display = 'none';
  };

  window.onclick = event => {
    if (event.target == modal) {
      modal.style.display = 'none';
    }
  };
});
