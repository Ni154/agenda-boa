import React, { useState, useEffect } from 'react';
import { useAuth } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
import { Badge } from './ui/badge';
import { 
  ShoppingCart, 
  Plus, 
  Minus, 
  Trash2, 
  User, 
  CreditCard,
  Receipt,
  Search,
  Package,
  Wrench
} from 'lucide-react';
import { toast } from 'sonner';

const POS = () => {
  const { api } = useAuth();
  const [produtos, setProdutos] = useState([]);
  const [servicos, setServicos] = useState([]);
  const [clientes, setClientes] = useState([]);
  const [carrinho, setCarrinho] = useState([]);
  const [clienteSelecionado, setClienteSelecionado] = useState(null);
  const [busca, setBusca] = useState('');
  const [activeTab, setActiveTab] = useState('produtos');
  const [showPagamento, setShowPagamento] = useState(false);
  const [formaPagamento, setFormaPagamento] = useState('');
  const [emitirNota, setEmitirNota] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [produtosRes, servicosRes, clientesRes] = await Promise.all([
        api.get('/produtos'),
        api.get('/servicos'),
        api.get('/clientes')
      ]);
      setProdutos(produtosRes.data);
      setServicos(servicosRes.data);
      setClientes(clientesRes.data);
    } catch (error) {
      toast.error('Erro ao carregar dados');
      console.error('Error loading data:', error);
    }
  };

  const adicionarAoCarrinho = (item, tipo) => {
    const itemExistente = carrinho.find(c => c.item_id === item.id && c.tipo === tipo);
    
    if (itemExistente) {
      setCarrinho(carrinho.map(c => 
        c.item_id === item.id && c.tipo === tipo
          ? { ...c, quantidade: c.quantidade + 1, total: (c.quantidade + 1) * c.preco_unitario }
          : c
      ));
    } else {
      const novoItem = {
        tipo,
        item_id: item.id,
        nome: item.nome,
        quantidade: 1,
        preco_unitario: item.preco,
        desconto: 0,
        total: item.preco
      };
      setCarrinho([...carrinho, novoItem]);
    }
    toast.success('Item adicionado ao carrinho');
  };

  const removerDoCarrinho = (index) => {
    setCarrinho(carrinho.filter((_, i) => i !== index));
    toast.success('Item removido do carrinho');
  };

  const alterarQuantidade = (index, novaQuantidade) => {
    if (novaQuantidade <= 0) return;
    
    setCarrinho(carrinho.map((item, i) => 
      i === index 
        ? { ...item, quantidade: novaQuantidade, total: novaQuantidade * item.preco_unitario }
        : item
    ));
  };

  const finalizarVenda = async () => {
    if (carrinho.length === 0) {
      toast.error('Carrinho vazio');
      return;
    }
    if (!formaPagamento) {
      toast.error('Selecione uma forma de pagamento');
      return;
    }

    setLoading(true);
    try {
      const vendaData = {
        cliente_id: clienteSelecionado?.id,
        cliente_nome: clienteSelecionado?.nome,
        itens: carrinho,
        forma_pagamento: formaPagamento,
        emitir_nota: emitirNota
      };

      await api.post('/vendas', vendaData);
      
      toast.success('Venda finalizada com sucesso!');
      
      // Reset
      setCarrinho([]);
      setClienteSelecionado(null);
      setFormaPagamento('');
      setEmitirNota(false);
      setShowPagamento(false);
      
      // Reload data to update stock
      loadData();
    } catch (error) {
      toast.error('Erro ao finalizar venda');
      console.error('Error finalizing sale:', error);
    } finally {
      setLoading(false);
    }
  };

  const calcularTotal = () => {
    return carrinho.reduce((total, item) => total + item.total, 0);
  };

  const filtrarItens = (items) => {
    if (!busca) return items;
    return items.filter(item => 
      item.nome.toLowerCase().includes(busca.toLowerCase()) ||
      (item.codigo && item.codigo.toLowerCase().includes(busca.toLowerCase()))
    );
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-800">POS - Ponto de Venda</h1>
          <p className="text-slate-600 mt-1">Sistema integrado de vendas</p>
        </div>
        <Badge variant="outline" className="self-start">
          {carrinho.length} itens no carrinho
        </Badge>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Product/Service Selection */}
        <div className="xl:col-span-2 space-y-6">
          {/* Search */}
          <Card className="shadow-soft border-0">
            <CardContent className="p-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" />
                <Input
                  placeholder="Buscar produtos ou serviços..."
                  value={busca}
                  onChange={(e) => setBusca(e.target.value)}
                  className="pl-10"
                />
              </div>
            </CardContent>
          </Card>

          {/* Tabs */}
          <div className="flex gap-2">
            <Button
              variant={activeTab === 'produtos' ? 'default' : 'outline'}
              onClick={() => setActiveTab('produtos')}
              className="flex items-center gap-2"
            >
              <Package className="w-4 h-4" />
              Produtos
            </Button>
            <Button
              variant={activeTab === 'servicos' ? 'default' : 'outline'}
              onClick={() => setActiveTab('servicos')}
              className="flex items-center gap-2"
            >
              <Wrench className="w-4 h-4" />
              Serviços
            </Button>
          </div>

          {/* Products Grid */}
          {activeTab === 'produtos' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {filtrarItens(produtos).map((produto) => (
                <Card key={produto.id} className="hover-lift cursor-pointer shadow-soft border-0">
                  <CardContent className="p-4">
                    <div className="flex justify-between items-start mb-3">
                      <h3 className="font-semibold text-slate-800 line-clamp-2">{produto.nome}</h3>
                      <Badge variant="secondary" className="ml-2">
                        {produto.estoque_atual}
                      </Badge>
                    </div>
                    <p className="text-sm text-slate-600 mb-3 line-clamp-2">{produto.descricao}</p>
                    <div className="flex justify-between items-center">
                      <span className="text-lg font-bold text-emerald-600">
                        R$ {produto.preco.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                      </span>
                      <Button
                        size="sm"
                        onClick={() => adicionarAoCarrinho(produto, 'produto')}
                        disabled={produto.estoque_atual <= 0}
                        className="bg-emerald-600 hover:bg-emerald-700"
                      >
                        <Plus className="w-4 h-4" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* Services Grid */}
          {activeTab === 'servicos' && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {filtrarItens(servicos).map((servico) => (
                <Card key={servico.id} className="hover-lift cursor-pointer shadow-soft border-0">
                  <CardContent className="p-4">
                    <h3 className="font-semibold text-slate-800 mb-3">{servico.nome}</h3>
                    <p className="text-sm text-slate-600 mb-3 line-clamp-2">{servico.descricao}</p>
                    <div className="flex justify-between items-center">
                      <div>
                        <span className="text-lg font-bold text-blue-600">
                          R$ {servico.preco.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                        </span>
                        <p className="text-xs text-slate-500">{servico.duracao_minutos}min</p>
                      </div>
                      <Button
                        size="sm"
                        onClick={() => adicionarAoCarrinho(servico, 'servico')}
                        className="bg-blue-600 hover:bg-blue-700"
                      >
                        <Plus className="w-4 h-4" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Cart */}
        <div className="space-y-6">
          {/* Client Selection */}
          <Card className="shadow-soft border-0">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-lg">
                <User className="w-5 h-5" />
                Cliente
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Select
                onValueChange={(value) => {
                  const cliente = clientes.find(c => c.id === value);
                  setClienteSelecionado(cliente);
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Selecionar cliente (opcional)" />
                </SelectTrigger>
                <SelectContent>
                  {clientes.map((cliente) => (
                    <SelectItem key={cliente.id} value={cliente.id}>
                      {cliente.nome}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </CardContent>
          </Card>

          {/* Cart Items */}
          <Card className="shadow-soft border-0">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-lg">
                <ShoppingCart className="w-5 h-5" />
                Carrinho ({carrinho.length})
              </CardTitle>
            </CardHeader>
            <CardContent className="max-h-96 overflow-y-auto">
              {carrinho.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  <ShoppingCart className="w-12 h-12 mx-auto mb-3 text-slate-400" />
                  <p>Carrinho vazio</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {carrinho.map((item, index) => (
                    <div key={index} className="bg-slate-50 rounded-lg p-3">
                      <div className="flex justify-between items-start mb-2">
                        <h4 className="font-medium text-slate-800 text-sm">{item.nome}</h4>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => removerDoCarrinho(index)}
                          className="text-red-500 hover:text-red-600 h-6 w-6 p-0"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => alterarQuantidade(index, item.quantidade - 1)}
                            className="h-6 w-6 p-0"
                          >
                            <Minus className="w-3 h-3" />
                          </Button>
                          <span className="text-sm font-medium w-8 text-center">{item.quantidade}</span>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => alterarQuantidade(index, item.quantidade + 1)}
                            className="h-6 w-6 p-0"
                          >
                            <Plus className="w-3 h-3" />
                          </Button>
                        </div>
                        <span className="font-semibold text-emerald-600">
                          R$ {item.total.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Total and Checkout */}
          {carrinho.length > 0 && (
            <Card className="shadow-soft border-0 bg-emerald-50 border-emerald-200">
              <CardContent className="p-4">
                <div className="flex justify-between items-center mb-4">
                  <span className="text-lg font-semibold text-slate-800">Total:</span>
                  <span className="text-2xl font-bold text-emerald-600">
                    R$ {calcularTotal().toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </span>
                </div>
                
                <Dialog open={showPagamento} onOpenChange={setShowPagamento}>
                  <DialogTrigger asChild>
                    <Button className="w-full bg-emerald-600 hover:bg-emerald-700 text-white">
                      <CreditCard className="w-4 h-4 mr-2" />
                      Finalizar Venda
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Finalizar Venda</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4">
                      <div>
                        <Label>Forma de Pagamento</Label>
                        <Select onValueChange={setFormaPagamento}>
                          <SelectTrigger>
                            <SelectValue placeholder="Selecionar forma de pagamento" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="dinheiro">Dinheiro</SelectItem>
                            <SelectItem value="cartao_debito">Cartão de Débito</SelectItem>
                            <SelectItem value="cartao_credito">Cartão de Crédito</SelectItem>
                            <SelectItem value="pix">PIX</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          id="emitir_nota"
                          checked={emitirNota}
                          onChange={(e) => setEmitirNota(e.target.checked)}
                          className="rounded"
                        />
                        <Label htmlFor="emitir_nota">Emitir nota fiscal?</Label>
                      </div>

                      <div className="pt-4 border-t">
                        <div className="flex justify-between items-center mb-4">
                          <span className="font-semibold">Total:</span>
                          <span className="text-xl font-bold text-emerald-600">
                            R$ {calcularTotal().toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                          </span>
                        </div>
                        <Button
                          onClick={finalizarVenda}
                          disabled={loading}
                          className="w-full bg-emerald-600 hover:bg-emerald-700"
                        >
                          {loading ? (
                            <div className="flex items-center gap-2">
                              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                              Processando...
                            </div>
                          ) : (
                            <>
                              <Receipt className="w-4 h-4 mr-2" />
                              Confirmar Venda
                            </>
                          )}
                        </Button>
                      </div>
                    </div>
                  </DialogContent>
                </Dialog>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};

export default POS;