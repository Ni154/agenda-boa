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
  Wrench, 
  Plus, 
  Search, 
  Edit, 
  Trash2, 
  Clock,
  DollarSign,
  Receipt,
  Percent
} from 'lucide-react';
import { toast } from 'sonner';

const Servicos = () => {
  const { api } = useAuth();
  const [servicos, setServicos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busca, setBusca] = useState('');
  const [showDialog, setShowDialog] = useState(false);
  const [editingServico, setEditingServico] = useState(null);
  const [formData, setFormData] = useState({
    nome: '',
    descricao: '',
    duracao_minutos: '',
    preco: '',
    aliquota_iss: '',
    codigo_servico_municipal: ''
  });

  useEffect(() => {
    loadServicos();
  }, []);

  const loadServicos = async () => {
    try {
      const response = await api.get('/servicos');
      setServicos(response.data);
    } catch (error) {
      toast.error('Erro ao carregar serviços');
      console.error('Error loading servicos:', error);
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
        duracao_minutos: parseInt(formData.duracao_minutos) || 60,
        preco: parseFloat(formData.preco) || 0,
        tributacao_iss: formData.aliquota_iss ? {
          aliquota: parseFloat(formData.aliquota_iss),
          codigo_servico_municipal: formData.codigo_servico_municipal || ''
        } : null
      };

      // Remove campos temporários
      delete data.aliquota_iss;
      delete data.codigo_servico_municipal;

      if (editingServico) {
        await api.put(`/servicos/${editingServico.id}`, data);
        toast.success('Serviço atualizado com sucesso!');
      } else {
        await api.post('/servicos', data);
        toast.success('Serviço cadastrado com sucesso!');
      }
      
      setShowDialog(false);
      resetForm();
      loadServicos();
    } catch (error) {
      toast.error('Erro ao salvar serviço');
      console.error('Error saving servico:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (servico) => {
    setEditingServico(servico);
    setFormData({
      nome: servico.nome || '',
      descricao: servico.descricao || '',
      duracao_minutos: servico.duracao_minutos?.toString() || '',
      preco: servico.preco?.toString() || '',
      aliquota_iss: servico.tributacao_iss?.aliquota?.toString() || '',
      codigo_servico_municipal: servico.tributacao_iss?.codigo_servico_municipal || ''
    });
    setShowDialog(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Tem certeza que deseja excluir este serviço?')) return;

    try {
      await api.delete(`/servicos/${id}`);
      toast.success('Serviço excluído com sucesso!');
      loadServicos();
    } catch (error) {
      toast.error('Erro ao excluir serviço');
      console.error('Error deleting servico:', error);
    }
  };

  const resetForm = () => {
    setFormData({
      nome: '',
      descricao: '',
      duracao_minutos: '',
      preco: '',
      aliquota_iss: '',
      codigo_servico_municipal: ''
    });
    setEditingServico(null);
  };

  const handleChange = (e) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  const filteredServicos = servicos.filter(servico =>
    servico.nome.toLowerCase().includes(busca.toLowerCase()) ||
    (servico.descricao && servico.descricao.toLowerCase().includes(busca.toLowerCase()))
  );

  const formatDuracao = (minutos) => {
    const horas = Math.floor(minutos / 60);
    const mins = minutos % 60;
    if (horas > 0) {
      return mins > 0 ? `${horas}h ${mins}min` : `${horas}h`;
    }
    return `${mins}min`;
  };

  if (loading && servicos.length === 0) {
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
          <h1 className="text-3xl font-bold text-slate-800">Serviços</h1>
          <p className="text-slate-600 mt-1">Gerencie seus serviços oferecidos</p>
        </div>
        <Dialog open={showDialog} onOpenChange={setShowDialog}>
          <DialogTrigger asChild>
            <Button onClick={resetForm} className="bg-blue-600 hover:bg-blue-700">
              <Plus className="w-4 h-4 mr-2" />
              Novo Serviço
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                {editingServico ? 'Editar Serviço' : 'Novo Serviço'}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label htmlFor="nome">Nome do Serviço *</Label>
                <Input
                  id="nome"
                  name="nome"
                  required
                  value={formData.nome}
                  onChange={handleChange}
                  placeholder="Nome do serviço"
                />
              </div>
              
              <div>
                <Label htmlFor="descricao">Descrição</Label>
                <Textarea
                  id="descricao"
                  name="descricao"
                  value={formData.descricao}
                  onChange={handleChange}
                  placeholder="Descrição detalhada do serviço"
                  rows={3}
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="duracao_minutos">Duração (minutos)</Label>
                  <Input
                    id="duracao_minutos"
                    name="duracao_minutos"
                    type="number"
                    min="1"
                    value={formData.duracao_minutos}
                    onChange={handleChange}
                    placeholder="60"
                  />
                </div>
                <div>
                  <Label htmlFor="preco">Preço (R$) *</Label>
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

              {/* Tributação ISS */}
              <div className="border-t pt-4">
                <h3 className="text-lg font-semibold text-slate-800 mb-3">Tributação ISS</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="aliquota_iss">Alíquota ISS (%)</Label>
                    <Input
                      id="aliquota_iss"
                      name="aliquota_iss"
                      type="number"
                      step="0.01"
                      min="0"
                      max="100"
                      value={formData.aliquota_iss}
                      onChange={handleChange}
                      placeholder="2,00"
                    />
                  </div>
                  <div>
                    <Label htmlFor="codigo_servico_municipal">Código Serviço Municipal</Label>
                    <Input
                      id="codigo_servico_municipal"
                      name="codigo_servico_municipal"
                      value={formData.codigo_servico_municipal}
                      onChange={handleChange}
                      placeholder="Ex: 14.01"
                    />
                  </div>
                </div>
                <p className="text-xs text-slate-500 mt-2">
                  Informações necessárias para emissão de NFS-e
                </p>
              </div>

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
                  className="flex-1 bg-blue-600 hover:bg-blue-700"
                >
                  {loading ? 'Salvando...' : editingServico ? 'Atualizar' : 'Cadastrar'}
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
              placeholder="Buscar serviços por nome ou descrição..."
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="shadow-soft border-0">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center border border-blue-200">
                <Wrench className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-800">{servicos.length}</p>
                <p className="text-sm text-slate-600">Total de Serviços</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="shadow-soft border-0">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-emerald-50 rounded-xl flex items-center justify-center border border-emerald-200">
                <DollarSign className="w-6 h-6 text-emerald-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-800">
                  R$ {(servicos.reduce((sum, s) => sum + s.preco, 0) / servicos.length || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                </p>
                <p className="text-sm text-slate-600">Preço Médio</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="shadow-soft border-0">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-purple-50 rounded-xl flex items-center justify-center border border-purple-200">
                <Receipt className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-800">
                  {servicos.filter(s => s.tributacao_iss).length}
                </p>
                <p className="text-sm text-slate-600">Com ISS Configurado</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Servicos Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredServicos.map((servico) => (
          <Card key={servico.id} className="hover-lift shadow-soft border-0">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <CardTitle className="text-lg truncate">{servico.nome}</CardTitle>
                  <div className="flex gap-2 mt-2">
                    <Badge variant="outline" className="text-blue-600">
                      <Clock className="w-3 h-3 mr-1" />
                      {formatDuracao(servico.duracao_minutos)}
                    </Badge>
                    {servico.tributacao_iss && (
                      <Badge variant="outline" className="text-purple-600">
                        <Percent className="w-3 h-3 mr-1" />
                        ISS {servico.tributacao_iss.aliquota}%
                      </Badge>
                    )}
                  </div>
                </div>
                <div className="flex gap-1">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleEdit(servico)}
                    className="h-8 w-8 p-0"
                  >
                    <Edit className="w-4 h-4" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleDelete(servico.id)}
                    className="h-8 w-8 p-0 text-red-500 hover:text-red-600"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            
            <CardContent>
              <div className="space-y-3">
                {servico.descricao && (
                  <p className="text-sm text-slate-600 line-clamp-3">{servico.descricao}</p>
                )}
                
                <div className="flex justify-between items-center pt-2 border-t border-slate-100">
                  <span className="text-2xl font-bold text-blue-600">
                    R$ {servico.preco.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                  </span>
                  <div className="text-right text-sm text-slate-500">
                    <p>Duração: {formatDuracao(servico.duracao_minutos)}</p>
                    {servico.tributacao_iss && (
                      <p>ISS: {servico.tributacao_iss.aliquota}%</p>
                    )}
                  </div>
                </div>

                {servico.tributacao_iss?.codigo_servico_municipal && (
                  <div className="text-xs text-slate-500 pt-2 border-t border-slate-50">
                    Cód. Municipal: {servico.tributacao_iss.codigo_servico_municipal}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredServicos.length === 0 && (
        <div className="text-center py-12">
          <Wrench className="w-16 h-16 mx-auto text-slate-400 mb-4" />
          <h3 className="text-lg font-semibold text-slate-600 mb-2">
            {busca ? 'Nenhum serviço encontrado' : 'Nenhum serviço cadastrado'}
          </h3>
          <p className="text-slate-500 mb-6">
            {busca 
              ? 'Tente ajustar os termos de busca'
              : 'Comece cadastrando seu primeiro serviço'
            }
          </p>
          {!busca && (
            <Button onClick={() => setShowDialog(true)} className="bg-blue-600 hover:bg-blue-700">
              <Plus className="w-4 h-4 mr-2" />
              Cadastrar Serviço
            </Button>
          )}
        </div>
      )}
    </div>
  );
};

export default Servicos;