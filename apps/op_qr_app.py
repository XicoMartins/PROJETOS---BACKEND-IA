"""Interface Windows para inserir QR Codes nas Ordens de Produção em PDF."""

from __future__ import annotations

import json
import os
import threading
import traceback
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core.op_qr_pdf import (
    AssociacaoOp,
    ProcessamentoCancelado,
    RegistroQr,
    analisar_pasta,
    localizar_raiz_qr,
    processar_associacoes,
)


APP_DIR = Path(os.environ.get("APPDATA", Path.home())) / "MTECH"
CONFIG_PATH = APP_DIR / "op_qr_config.json"


class Aplicativo(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MTECH - QR Codes nas OPs")
        self.geometry("1120x720")
        self.minsize(900, 580)
        self.configure(bg="#F3F5F7")
        self.associacoes: list[AssociacaoOp] = []
        self.ultima_saida: Path | None = None
        self.cancelamento = threading.Event()
        self._configurar_estilo()
        self._criar_interface()
        self._carregar_preferencias()

    def _configurar_estilo(self):
        estilo = ttk.Style(self)
        estilo.theme_use("vista")
        estilo.configure("Titulo.TLabel", font=("Segoe UI", 18, "bold"), foreground="#1F4E5F")
        estilo.configure("Sub.TLabel", font=("Segoe UI", 10), foreground="#50616B")
        estilo.configure("Acao.TButton", font=("Segoe UI", 10, "bold"), padding=8)
        estilo.configure("Treeview", rowheight=28, font=("Segoe UI", 9))
        estilo.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    def _criar_interface(self):
        topo = ttk.Frame(self, padding=(18, 14))
        topo.pack(fill="x")
        ttk.Label(topo, text="QR Codes nas Ordens de Produção", style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(
            topo,
            text="Selecione as pastas, revise as associações e gere os PDFs prontos para impressão.",
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        caminhos = ttk.LabelFrame(self, text="Pastas", padding=12)
        caminhos.pack(fill="x", padx=18, pady=(0, 10))
        self.pasta_ops = tk.StringVar()
        self.pasta_qrs = tk.StringVar()
        self._linha_pasta(caminhos, 0, "Pasta das OPs em PDF", self.pasta_ops, self._selecionar_ops)
        self._linha_pasta(caminhos, 1, "Pasta dos QR Codes", self.pasta_qrs, self._selecionar_qrs)

        opcoes = ttk.Frame(caminhos)
        opcoes.grid(row=2, column=1, columnspan=2, sticky="w", pady=(8, 0))
        self.substituir = tk.BooleanVar(value=False)
        self.reprocessar = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            opcoes,
            text="Substituir PDFs originais (backup obrigatório)",
            variable=self.substituir,
        ).pack(side="left", padx=(0, 20))
        ttk.Checkbutton(
            opcoes,
            text="Permitir reprocessar PDFs que já possuem QR",
            variable=self.reprocessar,
        ).pack(side="left")
        caminhos.columnconfigure(1, weight=1)

        botoes = ttk.Frame(self, padding=(18, 0, 18, 10))
        botoes.pack(fill="x")
        self.botao_analisar = ttk.Button(
            botoes, text="1. Analisar e associar", style="Acao.TButton", command=self.analisar
        )
        self.botao_analisar.pack(side="left")
        self.botao_editar = ttk.Button(
            botoes, text="Revisar selecionado", command=self.editar_associacao, state="disabled"
        )
        self.botao_editar.pack(side="left", padx=8)
        self.botao_processar = ttk.Button(
            botoes, text="2. Gerar PDFs com QR", style="Acao.TButton", command=self.processar, state="disabled"
        )
        self.botao_processar.pack(side="left")
        self.botao_cancelar = ttk.Button(
            botoes,
            text="Cancelar",
            command=self.cancelar_processo,
            state="disabled",
        )
        self.botao_cancelar.pack(side="left", padx=8)
        self.botao_abrir = ttk.Button(
            botoes, text="Abrir pasta de resultado", command=self.abrir_saida, state="disabled"
        )
        self.botao_abrir.pack(side="right")

        tabela_frame = ttk.Frame(self, padding=(18, 0, 18, 8))
        tabela_frame.pack(fill="both", expand=True)
        colunas = ("pdf", "produto", "operacao", "ids", "status")
        self.tabela = ttk.Treeview(tabela_frame, columns=colunas, show="headings", selectmode="browse")
        titulos = {
            "pdf": "PDF",
            "produto": "Produto",
            "operacao": "Operação",
            "ids": "PROCESSO_ID",
            "status": "Situação",
        }
        larguras = {"pdf": 100, "produto": 220, "operacao": 260, "ids": 190, "status": 250}
        for coluna in colunas:
            self.tabela.heading(coluna, text=titulos[coluna])
            self.tabela.column(coluna, width=larguras[coluna], minwidth=80)
        barra_y = ttk.Scrollbar(tabela_frame, orient="vertical", command=self.tabela.yview)
        barra_x = ttk.Scrollbar(tabela_frame, orient="horizontal", command=self.tabela.xview)
        self.tabela.configure(yscrollcommand=barra_y.set, xscrollcommand=barra_x.set)
        self.tabela.grid(row=0, column=0, sticky="nsew")
        barra_y.grid(row=0, column=1, sticky="ns")
        barra_x.grid(row=1, column=0, sticky="ew")
        tabela_frame.rowconfigure(0, weight=1)
        tabela_frame.columnconfigure(0, weight=1)
        self.tabela.bind("<Double-1>", lambda _evento: self.editar_associacao())
        self.tabela.bind("<<TreeviewSelect>>", lambda _evento: self.botao_editar.configure(state="normal"))
        self.tabela.tag_configure("ok", background="#E7F5EA")
        self.tabela.tag_configure("manual", background="#E8F2FB")
        self.tabela.tag_configure("revisar", background="#FFF4D6")
        self.tabela.tag_configure("erro", background="#FCE4E4")

        rodape = ttk.Frame(self, padding=(18, 4, 18, 12))
        rodape.pack(fill="x")
        self.status = tk.StringVar(value="Pronto.")
        ttk.Label(rodape, textvariable=self.status).pack(side="left")
        self.progresso = ttk.Progressbar(rodape, mode="indeterminate", length=180)
        self.progresso.pack(side="right")

    def _linha_pasta(self, frame, linha, rotulo, variavel, comando):
        ttk.Label(frame, text=rotulo).grid(row=linha, column=0, sticky="w", padx=(0, 10), pady=4)
        ttk.Entry(frame, textvariable=variavel).grid(row=linha, column=1, sticky="ew", pady=4)
        ttk.Button(frame, text="Selecionar...", command=comando).grid(row=linha, column=2, padx=(8, 0), pady=4)

    def _selecionar_ops(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta que contém as OPs em PDF")
        if pasta:
            self.pasta_ops.set(pasta)

    def _selecionar_qrs(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta base dos QR Codes")
        if pasta:
            self.pasta_qrs.set(pasta)

    def _carregar_preferencias(self):
        try:
            dados = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError, OSError):
            return
        self.pasta_ops.set(dados.get("pasta_ops", ""))
        self.pasta_qrs.set(dados.get("pasta_qrs", ""))

    def _salvar_preferencias(self):
        APP_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(
                {"pasta_ops": self.pasta_ops.get(), "pasta_qrs": self.pasta_qrs.get()},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _ocupado(self, valor: bool, mensagem: str, indeterminado: bool = True):
        estado = "disabled" if valor else "normal"
        self.botao_analisar.configure(state=estado)
        self.botao_processar.configure(state="disabled" if valor else self._estado_processar())
        self.botao_cancelar.configure(state="normal" if valor else "disabled")
        self.status.set(mensagem)
        if valor:
            if indeterminado:
                self.progresso.configure(mode="indeterminate")
                self.progresso.start(12)
            else:
                self.progresso.stop()
                self.progresso.configure(mode="determinate", value=0)
        else:
            self.progresso.stop()

    def _estado_processar(self):
        return "normal" if self.associacoes and all(a.status in {"ok", "manual"} for a in self.associacoes) else "disabled"

    def _em_thread(self, funcao, sucesso):
        def executar():
            try:
                resultado = funcao()
            except ProcessamentoCancelado:
                self.after(0, self._cancelado)
            except Exception as exc:
                detalhes = traceback.format_exc()
                self.after(0, lambda: self._erro(str(exc), detalhes))
            else:
                self.after(0, lambda: sucesso(resultado))
        threading.Thread(target=executar, daemon=True).start()

    def cancelar_processo(self):
        self.cancelamento.set()
        self.botao_cancelar.configure(state="disabled")
        self.status.set("Cancelamento solicitado; finalizando a etapa atual com segurança...")

    def _cancelado(self):
        self._ocupado(False, "Processamento cancelado. Nenhum PDF parcial foi mantido.")
        self.progresso.configure(value=0)
        messagebox.showinfo("Processamento cancelado", "A operação foi cancelada com segurança.")

    def _erro(self, mensagem, detalhes):
        self._ocupado(False, "Falha. Revise a mensagem apresentada.")
        messagebox.showerror("Não foi possível concluir", f"{mensagem}\n\nDetalhes técnicos:\n{detalhes[-1500:]}")

    def analisar(self):
        ops, qrs = Path(self.pasta_ops.get().strip()), Path(self.pasta_qrs.get().strip())
        if not ops.is_dir() or not qrs.is_dir():
            messagebox.showwarning("Pastas inválidas", "Selecione a pasta das OPs e a pasta dos QR Codes.")
            return
        try:
            qrs = localizar_raiz_qr(qrs)
        except FileNotFoundError as exc:
            messagebox.showwarning("Pasta de QR Codes inválida", str(exc))
            return
        self.pasta_qrs.set(str(qrs))
        total_pdfs = sum(1 for item in ops.glob("*.pdf") if item.is_file())
        if not total_pdfs:
            messagebox.showwarning("Sem PDFs", "Nenhum PDF foi encontrado na pasta das OPs.")
            return
        self._salvar_preferencias()
        self.cancelamento.clear()
        self.progresso.configure(maximum=total_pdfs)
        self._ocupado(
            True,
            f"Preparando análise de {total_pdfs} PDFs...",
            indeterminado=False,
        )
        self._em_thread(
            lambda: analisar_pasta(
                ops,
                qrs,
                self._progresso_analise,
                self.cancelamento.is_set,
            ),
            self._analise_concluida,
        )

    def _progresso_analise(self, atual: int, total: int, arquivo: str):
        self.after(
            0,
            lambda: (
                self.progresso.configure(value=atual, maximum=total),
                self.status.set(f"Analisando PDF {atual} de {total}: {arquivo}"),
            ),
        )

    def _analise_concluida(self, associacoes):
        self.associacoes = associacoes
        self._atualizar_tabela()
        revisar = sum(item.status not in {"ok", "manual"} for item in associacoes)
        self._ocupado(False, f"Análise concluída: {len(associacoes)} PDFs; {revisar} precisam de revisão.")
        if revisar:
            messagebox.showinfo("Revisão necessária", "Os itens amarelos ou vermelhos precisam ser revisados antes de gerar os PDFs.")

    def _atualizar_tabela(self):
        self.tabela.delete(*self.tabela.get_children())
        for indice, item in enumerate(self.associacoes):
            ids = ", ".join(registro.processo_id for registro in item.registros) or "-"
            self.tabela.insert(
                "", "end", iid=str(indice),
                values=(item.dados.arquivo.name, item.dados.produto, item.dados.operacao, ids, item.mensagem),
                tags=(item.status,),
            )
        self.botao_processar.configure(state=self._estado_processar())

    def editar_associacao(self):
        selecionado = self.tabela.selection()
        if not selecionado:
            return
        indice = int(selecionado[0])
        associacao = self.associacoes[indice]
        candidatos = associacao.candidatos or associacao.registros
        if not candidatos:
            messagebox.showwarning("Sem candidatos", "Não há candidatos para esta OP. Confirme se o produto existe no manifesto.")
            return

        janela = tk.Toplevel(self)
        janela.title(f"Revisar {associacao.dados.arquivo.name}")
        janela.geometry("760x480")
        janela.transient(self)
        janela.grab_set()
        ttk.Label(janela, text=associacao.dados.operacao, font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=14, pady=(14, 2))
        ttk.Label(janela, text="Selecione um ou mais processos correspondentes:").pack(anchor="w", padx=14, pady=(0, 8))
        lista = tk.Listbox(janela, selectmode="extended", font=("Consolas", 9))
        lista.pack(fill="both", expand=True, padx=14, pady=4)
        selecionados = {item.processo_id for item in associacao.registros}
        for posicao, item in enumerate(candidatos):
            lista.insert("end", f"{item.processo_id} | {item.processo} | {item.ferramental}")
            if item.processo_id in selecionados:
                lista.selection_set(posicao)

        def confirmar():
            indices = lista.curselection()
            if not indices:
                messagebox.showwarning("Seleção obrigatória", "Selecione pelo menos um processo.", parent=janela)
                return
            associacao.registros = [candidatos[i] for i in indices]
            associacao.status = "manual"
            associacao.mensagem = "Associação confirmada manualmente"
            janela.destroy()
            self._atualizar_tabela()

        ttk.Button(janela, text="Confirmar associação", style="Acao.TButton", command=confirmar).pack(pady=12)

    def processar(self):
        if self._estado_processar() != "normal":
            return
        substituir = self.substituir.get()
        if substituir and not messagebox.askyesno(
            "Substituir originais",
            "Os PDFs originais serão substituídos após a criação de um backup. Deseja continuar?",
        ):
            return
        qrs = Path(self.pasta_qrs.get().strip())
        self.cancelamento.clear()
        self.progresso.configure(maximum=len(self.associacoes))
        self._ocupado(
            True,
            f"Preparando {len(self.associacoes)} PDFs em pasta local...",
            indeterminado=False,
        )
        self._em_thread(
            lambda: processar_associacoes(
                self.associacoes,
                qrs,
                substituir_originais=substituir,
                permitir_reprocessar=self.reprocessar.get(),
                progresso=self._progresso_processamento,
                cancelar=self.cancelamento.is_set,
            ),
            self._processamento_concluido,
        )

    def _progresso_processamento(
        self, fase: str, atual: int, total: int, arquivo: str
    ):
        rotulos = {
            "gerando": "Gerando localmente",
            "validando": "Validando resultado",
            "backup": "Criando backup",
            "salvando": "Salvando na pasta final",
        }
        rotulo = rotulos.get(fase, fase.capitalize())
        self.after(
            0,
            lambda: (
                self.progresso.configure(value=atual, maximum=total),
                self.status.set(f"{rotulo} {atual} de {total}: {arquivo}"),
            ),
        )

    def _processamento_concluido(self, resultado):
        pasta, relatorio = resultado
        self.ultima_saida = pasta
        self.botao_abrir.configure(state="normal")
        self._ocupado(False, f"Concluído: {relatorio['pdfs']} PDFs e {relatorio['associacoes_qr']} associações de QR.")
        messagebox.showinfo("Processamento concluído", f"PDFs prontos em:\n{pasta}")

    def abrir_saida(self):
        if self.ultima_saida and self.ultima_saida.exists():
            os.startfile(self.ultima_saida)


if __name__ == "__main__":
    Aplicativo().mainloop()
