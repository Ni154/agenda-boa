import React, { useState, useEffect } from 'react';
import { useAuth } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Textarea } from './ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
import { Badge } from './ui/badge';
import { 
  Package, 
  Plus, 
  Search, 
  Edit, 
  Trash2, 
  DollarSign,
  BarChart3,
  AlertTriangle,
  TrendingUp
} from 'lucide-react';
import { toast } from 'sonner';

const Produtos = () => {
  const { api } = useAuth();
  const [produtos, setProdutos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busca, setBusca] = useState('');
  const [showDialog, setShowDialog] = useState(false);
  const [editingProduto, setEditingProduto] = useState(null);
  const [formData, setFormData] = useState({
    codigo: '',
    nome: '',
    descricao: '',
    categoria: '',
    ncm: '',
    custo: '',
    preco: '',
    estoque_atual: '',
    estoque_minimo: ''
  });

  useEffect(() => {
    loadProdutos();
  }, []);

  const loadProdutos = async () => {
    try {
      const response = await api.get('/produtos');
      setProdutos(response.data);
    } catch (error) {
      toast.error('Erro ao carregar produtos');
      console.error('Error loading produtos:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const data = {
        ...formData,
        custo: parseFloat(formData.custo) || 0,
        preco: parseFloat(formData.preco) || 0,
        estoque_atual: parseInt(formData.estoque_atual) || 0,
        estoque_minimo: parseInt(formData.estoque_minimo) || 0
      };

      if (editingProduto) {
        await api.put(`/produtos/${editingProduto.id}`, data);
        toast.success('Produto atualizado com sucesso!');
      } else {
        await api.post('/produtos', data);
        toast.success('Produto cadastrado com sucesso!');
      }
      
      setShowDialog(false);
      resetForm();
      loadProdutos();
    } catch (error) {
      toast.error('Erro ao salvar produto');
      console.error('Error saving produto:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (produto) => {
    setEditingProduto(produto);
    setFormData({
      codigo: produto.codigo || '',
      nome: produto.nome || '',
      descricao: produto.descricao || '',
      categoria: produto.categoria || '',
      ncm: produto.ncm || '',
      custo: produto.custo?.toString() || '',
      preco: produto.preco?.toString() || '',
      estoque_atual: produto.estoque_atual?.toString() || '',
      estoque_minimo: produto.estoque_minimo?.toString() || ''
    });
    setShowDialog(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Tem certeza que deseja excluir este produto?')) return;

    try {
      await api.delete(`/produtos/${id}`);
      toast.success('Produto excluído com sucesso!');
      loadProdutos();
    } catch (error) {
      toast.error('Erro ao excluir produto');
      console.error('Error deleting produto:', error);
    }
  };

  const resetForm = () => {
    setFormData({
      codigo: '',
      nome: '',
      descricao: '',
      categoria: '',
      ncm: '',
      custo: '',
      preco: '',
      estoque_atual: '',
      estoque_minimo: ''
    });
    setEditingProduto(null);
  };

  const handleChange = (e) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  const filteredProdutos = produtos.filter(produto =>
    produto.nome.toLowerCase().includes(busca.toLowerCase()) ||
    (produto.codigo && produto.codigo.toLowerCase().includes(busca.toLowerCase())) ||
    (produto.categoria && produto.categoria.toLowerCase().includes(busca.toLowerCase()))
  );

  const getEstoqueStatus = (produto) => {
    if (produto.estoque_atual <= 0) return 'out';
    if (produto.estoque_atual <= produto.estoque_minimo) return 'low';
    return 'ok';
  };

  const getEstoqueColor = (status) => {
    switch (status) {
      case 'out': return 'bg-red-50 text-red-700 border-red-200';
      case 'low': return 'bg-yellow-50 text-yellow-700 border-yellow-200';
      default: return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    }
  };

  const getEstoqueText = (status) => {
    switch (status) {
      case 'out': return 'Sem Estoque';
      case 'low': return 'Estoque Baixo';
      default: return 'Em Estoque';
    }
  };

  const calcularMargem = (custo, preco) => {
    if (!custo || !preco || custo === 0) return 0;
    return ((preco - custo) / preco * 100);
  };

  if (loading && produtos.length === 0) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-slate-200 rounded w-1/4 mb-4"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-40 bg-slate-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-800">Produtos</h1>
          <p className="text-slate-600 mt-1">Gerencie seu estoque de produtos</p>
        </div>
        <Dialog open={showDialog} onOpenChange={setShowDialog}>
          <DialogTrigger asChild>
            <Button onClick={resetForm} className="bg-emerald-600 hover:bg-emerald-700">
              <Plus className="w-4 h-4 mr-2" />
              Novo Produto
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                {editingProduto ? 'Editar Produto' : 'Novo Produto'}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="codigo">Código</Label>
                  <Input
                    id="codigo"
                    name="codigo"
                    value={formData.codigo}
                    onChange={handleChange}
                    placeholder="Código do produto"
                  />
                </div>
                <div>
                  <Label htmlFor="nome">Nome *</Label>
                  <Input
                    id="nome"
                    name="nome"
                    required
                    value={formData.nome}
                    onChange={handleChange}
                    placeholder="Nome do produto"
                  />
                </div>
              </div>
              
              <div>
                <Label htmlFor="descricao">Descrição</Label>
                <Textarea
                  id="descricao"
                  name="descricao"
                  value={formData.descricao}
                  onChange={handleChange}
                  placeholder="Descrição detalhada do produto"
                  rows={3}
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="categoria">Categoria</Label>
                  <Input
                    id="categoria"
                    name="categoria"
                    value={formData.categoria}
                    onChange={handleChange}
                    placeholder="Categoria do produto"
                  />
                </div>
                <div>
                  <Label htmlFor="ncm">NCM</Label>
                  <Input
                    id="ncm"
                    name="ncm"
                    value={formData.ncm}
                    onChange={handleChange}
                    placeholder="Código NCM"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="custo">Custo (R$)</Label>
                  <Input
                    id="custo"
                    name="custo"
                    type="number"
                    step="0.01"
                    min="0"
                    value={formData.custo}
                    onChange={handleChange}
                    placeholder="0,00"
                  />
                </div>
                <div>
                  <Label htmlFor="preco">Preço de Venda (R$) *</Label>
                  <Input
                    id="preco"
                    name="preco"
                    type="number"
                    step="0.01"
                    min="0"
                    required
                    value={formData.preco}
                    onChange={handleChange}
                    placeholder="0,00"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="estoque_atual">Estoque Atual</Label>
                  <Input
                    id="estoque_atual"
                    name="estoque_atual"
                    type="number"
                    min="0"
                    value={formData.estoque_atual}
                    onChange={handleChange}
                    placeholder="0"
                  />
                </div>
                <div>
                  <Label htmlFor="estoque_minimo">Estoque Mínimo</Label>
                  <Input
                    id="estoque_minimo"
                    name="estoque_minimo"
                    type="number"
                    min="0"
                    value={formData.estoque_minimo}
                    onChange={handleChange}
                    placeholder="0"
                  />
                </div>
              </div>

              {formData.custo && formData.preco && (
                <div className="p-3 bg-slate-50 rounded-lg">
                  <p className="text-sm text-slate-600">
                    Margem de Lucro: <span className="font-semibold text-emerald-600">
                      {calcularMargem(parseFloat(formData.custo), parseFloat(formData.preco)).toFixed(1)}%
                    </span>
                  </p>
                </div>
              )}

              <div className="flex gap-3 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowDialog(false)}
                  className="flex-1"
                >
                  Cancelar
                </Button>
                <Button
                  type="submit"
                  disabled={loading}
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700"
                >
                  {loading ? 'Salvando...' : editingProduto ? 'Atualizar' : 'Cadastrar'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Search */}
      <Card className="shadow-soft border-0">
        <CardContent className="p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" />
            <Input
              placeholder="Buscar produtos por nome, código ou categoria..."
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="shadow-soft border-0">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center border border-blue-200">
                <Package className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-800">{produtos.length}</p>
                <p className="text-sm text-slate-600">Total de Produtos</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="shadow-soft border-0">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-emerald-50 rounded-xl flex items-center justify-center border border-emerald-200">
                <BarChart3 className="w-6 h-6 text-emerald-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-800">
                  {produtos.reduce((sum, p) => sum + p.estoque_atual, 0)}
                </p>
                <p className="text-sm text-slate-600">Itens em Estoque</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="shadow-soft border-0">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-yellow-50 rounded-xl flex items-center justify-center border border-yellow-200">
                <AlertTriangle className="w-6 h-6 text-yellow-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-800">
                  {produtos.filter(p => p.estoque_atual <= p.estoque_minimo).length}
                </p>
                <p className="text-sm text-slate-600">Estoque Baixo</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-soft border-0">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-purple-50 rounded-xl flex items-center justify-center border border-purple-200">
                <TrendingUp className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-800">
                  R$ {produtos.reduce((sum, p) => sum + (p.custo * p.estoque_atual), 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                </p>
                <p className="text-sm text-slate-600">Valor do Estoque</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Produtos Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredProdutos.map((produto) => {
          const estoqueStatus = getEstoqueStatus(produto);
          const margem = calcularMargem(produto.custo, produto.preco);
          
          return (
            <Card key={produto.id} className="hover-lift shadow-soft border-0">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-lg truncate">{produto.nome}</CardTitle>
                    {produto.codigo && (
                      <p className="text-sm text-slate-500">Cód: {produto.codigo}</p>
                    )}
                    {produto.categoria && (
                      <Badge variant="outline" className="mt-1 text-xs">
                        {produto.categoria}
                      </Badge>
                    )}
                  </div>
                  <div className="flex gap-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleEdit(produto)}
                      className="h-8 w-8 p-0"
                    >
                      <Edit className="w-4 h-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDelete(produto.id)}
                      className="h-8 w-8 p-0 text-red-500 hover:text-red-600"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              
              <CardContent>
                <div className="space-y-3">
                  {produto.descricao && (
                    <p className="text-sm text-slate-600 line-clamp-2">{produto.descricao}</p>
                  )}
                  
                  <div className="flex justify-between items-center">
                    <div>
                      <p className="text-lg font-bold text-emerald-600">
                        R$ {produto.preco.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                      </p>
                      {produto.custo > 0 && (
                        <p className="text-sm text-slate-500">
                          Custo: R$ {produto.custo.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                        </p>
                      )}
                    </div>
                    {margem > 0 && (
                      <Badge variant="outline" className="text-emerald-600">
                        {margem.toFixed(1)}% margem
                      </Badge>
                    )}
                  </div>

                  <div className="flex justify-between items-center pt-2 border-t border-slate-100">
                    <Badge className={`border ${getEstoqueColor(estoqueStatus)}`}>
                      {getEstoqueText(estoqueStatus)}
                    </Badge>
                    <span className="text-sm font-medium text-slate-700">
                      {produto.estoque_atual} unidades
                    </span>
                  </div>

                  {produto.ncm && (
                    <div className="text-xs text-slate-500">
                      NCM: {produto.ncm}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {filteredProdutos.length === 0 && (
        <div className="text-center py-12">
          <Package className="w-16 h-16 mx-auto text-slate-400 mb-4" />
          <h3 className="text-lg font-semibold text-slate-600 mb-2">
            {busca ? 'Nenhum produto encontrado' : 'Nenhum produto cadastrado'}
          </h3>
          <p className="text-slate-500 mb-6">
            {busca 
              ? 'Tente ajustar os termos de busca'
              : 'Comece cadastrando seu primeiro produto'
            }
          </p>
          {!busca && (
            <Button onClick={() => setShowDialog(true)} className="bg-emerald-600 hover:bg-emerald-700">
              <Plus className="w-4 h-4 mr-2" />
              Cadastrar Produto
            </Button>
          )}
        </div>
      )}
    </div>
  );
};

export default Produtos;