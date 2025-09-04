import React, { useState, useEffect } from 'react';
import { useAuth } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
import { Badge } from './ui/badge';
import { Calendar } from './ui/calendar';
import { 
  Calendar as CalendarIcon, 
  Plus, 
  Search, 
  Edit, 
  Trash2, 
  Clock,
  User,
  Wrench,
  ShoppingCart,
  CheckCircle,
  XCircle
} from 'lucide-react';
import { toast } from 'sonner';
import { format, parseISO } from 'date-fns';
import { ptBR } from 'date-fns/locale';

const Agendamentos = () => {
  const { api } = useAuth();
  const [agendamentos, setAgendamentos] = useState([]);
  const [clientes, setClientes] = useState([]);
  const [servicos, setServicos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busca, setBusca] = useState('');
  const [showDialog, setShowDialog] = useState(false);
  const [editingAgendamento, setEditingAgendamento] = useState(null);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [formData, setFormData] = useState({
    cliente_id: '',
    servico_id: '',
    data: '',
    hora: '',
    observacoes: '',
    status: 'agendado'
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [agendamentosRes, clientesRes, servicosRes] = await Promise.all([
        api.get('/agendamentos'),
        api.get('/clientes'),
        api.get('/servicos')
      ]);
      setAgendamentos(agendamentosRes.data || []);
      setClientes(clientesRes.data);
      setServicos(servicosRes.data);
    } catch (error) {
      toast.error('Erro ao carregar dados');
      console.error('Error loading data:', error);
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
        data_hora: `${formData.data}T${formData.hora}:00`
      };
      delete data.data;
      delete data.hora;

      if (editingAgendamento) {
        await api.put(`/agendamentos/${editingAgendamento.id}`, data);
        toast.success('Agendamento atualizado com sucesso!');
      } else {
        await api.post('/agendamentos', data);
        toast.success('Agendamento cadastrado com sucesso!');
      }
      
      setShowDialog(false);
      resetForm();
      loadData();
    } catch (error) {
      toast.error('Erro ao salvar agendamento');
      console.error('Error saving agendamento:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (agendamento) => {
    setEditingAgendamento(agendamento);
    const dataHora = new Date(agendamento.data_hora);
    setFormData({
      cliente_id: agendamento.cliente_id || '',
      servico_id: agendamento.servico_id || '',
      data: format(dataHora, 'yyyy-MM-dd'),
      hora: format(dataHora, 'HH:mm'),
      observacoes: agendamento.observacoes || '',
      status: agendamento.status || 'agendado'
    });
    setShowDialog(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Tem certeza que deseja excluir este agendamento?')) return;

    try {
      await api.delete(`/agendamentos/${id}`);
      toast.success('Agendamento excluído com sucesso!');
      loadData();
    } catch (error) {
      toast.error('Erro ao excluir agendamento');
      console.error('Error deleting agendamento:', error);
    }
  };

  const transformarEmVenda = async (agendamento) => {
    try {
      // Navigate to POS with pre-filled data
      window.location.href = `/pos?cliente=${agendamento.cliente_id}&servico=${agendamento.servico_id}`;
      toast.success('Redirecionando para o POS...');
    } catch (error) {
      toast.error('Erro ao transformar em venda');
      console.error('Error transforming to sale:', error);
    }
  };

  const resetForm = () => {
    setFormData({
      cliente_id: '',
      servico_id: '',
      data: format(new Date(), 'yyyy-MM-dd'),
      hora: '09:00',
      observacoes: '',
      status: 'agendado'
    });
    setEditingAgendamento(null);
  };

  const handleChange = (name, value) => {
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'agendado': return 'bg-blue-50 text-blue-700 border-blue-200';
      case 'confirmado': return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'realizado': return 'bg-green-50 text-green-700 border-green-200';
      case 'cancelado': return 'bg-red-50 text-red-700 border-red-200';
      default: return 'bg-slate-50 text-slate-700 border-slate-200';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'agendado': return 'Agendado';
      case 'confirmado': return 'Confirmado';
      case 'realizado': return 'Realizado';
      case 'cancelado': return 'Cancelado';
      default: return status;
    }
  };

  const filteredAgendamentos = agendamentos.filter(agendamento => {
    const cliente = clientes.find(c => c.id === agendamento.cliente_id);
    const servico = servicos.find(s => s.id === agendamento.servico_id);
    
    return (
      (cliente?.nome.toLowerCase().includes(busca.toLowerCase())) ||
      (servico?.nome.toLowerCase().includes(busca.toLowerCase())) ||
      (agendamento.observacoes?.toLowerCase().includes(busca.toLowerCase()))
    );
  });

  // Group agendamentos by date
  const agendamentosPorData = filteredAgendamentos.reduce((acc, agendamento) => {
    const data = format(new Date(agendamento.data_hora), 'yyyy-MM-dd');
    if (!acc[data]) acc[data] = [];
    acc[data].push(agendamento);
    return acc;
  }, {});

  // Sort dates
  const datasSortidas = Object.keys(agendamentosPorData).sort();

  if (loading && agendamentos.length === 0) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-slate-200 rounded w-1/4 mb-4"></div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-4">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-24 bg-slate-200 rounded"></div>
              ))}
            </div>
            <div className="h-80 bg-slate-200 rounded"></div>
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
          <h1 className="text-3xl font-bold text-slate-800">Agendamentos</h1>
          <p className="text-slate-600 mt-1">Gerencie sua agenda de serviços</p>
        </div>
        <Dialog open={showDialog} onOpenChange={setShowDialog}>
          <DialogTrigger asChild>
            <Button onClick={resetForm} className="bg-purple-600 hover:bg-purple-700">
              <Plus className="w-4 h-4 mr-2" />
              Novo Agendamento
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>
                {editingAgendamento ? 'Editar Agendamento' : 'Novo Agendamento'}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label>Cliente *</Label>
                  <Select onValueChange={(value) => handleChange('cliente_id', value)} value={formData.cliente_id}>
                    <SelectTrigger>
                      <SelectValue placeholder="Selecionar cliente" />
                    </SelectTrigger>
                    <SelectContent>
                      {clientes.map((cliente) => (
                        <SelectItem key={cliente.id} value={cliente.id}>
                          {cliente.nome}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Serviço *</Label>
                  <Select onValueChange={(value) => handleChange('servico_id', value)} value={formData.servico_id}>
                    <SelectTrigger>
                      <SelectValue placeholder="Selecionar serviço" />
                    </SelectTrigger>
                    <SelectContent>
                      {servicos.map((servico) => (
                        <SelectItem key={servico.id} value={servico.id}>
                          {servico.nome} - R$ {servico.preco.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="data">Data *</Label>
                  <Input
                    id="data"
                    type="date"
                    required
                    value={formData.data}
                    onChange={(e) => handleChange('data', e.target.value)}
                  />
                </div>
                <div>
                  <Label htmlFor="hora">Hora *</Label>
                  <Input
                    id="hora"
                    type="time"
                    required
                    value={formData.hora}
                    onChange={(e) => handleChange('hora', e.target.value)}
                  />
                </div>
              </div>

              <div>
                <Label>Status</Label>
                <Select onValueChange={(value) => handleChange('status', value)} value={formData.status}>
                  <SelectTrigger>
                    <SelectValue placeholder="Selecionar status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="agendado">Agendado</SelectItem>
                    <SelectItem value="confirmado">Confirmado</SelectItem>
                    <SelectItem value="realizado">Realizado</SelectItem>
                    <SelectItem value="cancelado">Cancelado</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="observacoes">Observações</Label>
                <Input
                  id="observacoes"
                  value={formData.observacoes}
                  onChange={(e) => handleChange('observacoes', e.target.value)}
                  placeholder="Observações do agendamento"
                />
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
                  className="flex-1 bg-purple-600 hover:bg-purple-700"
                >
                  {loading ? 'Salvando...' : editingAgendamento ? 'Atualizar' : 'Cadastrar'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-3 space-y-6">
          {/* Search */}
          <Card className="shadow-soft border-0">
            <CardContent className="p-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-5 h-5" />
                <Input
                  placeholder="Buscar agendamentos por cliente, serviço ou observações..."
                  value={busca}
                  onChange={(e) => setBusca(e.target.value)}
                  className="pl-10"
                />
              </div>
            </CardContent>
          </Card>

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card className="shadow-soft border-0">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center">
                    <CalendarIcon className="w-5 h-5 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-lg font-bold text-slate-800">
                      {agendamentos.filter(a => a.status === 'agendado').length}
                    </p>
                    <p className="text-xs text-slate-600">Agendados</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="shadow-soft border-0">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-emerald-50 rounded-lg flex items-center justify-center">
                    <CheckCircle className="w-5 h-5 text-emerald-600" />
                  </div>
                  <div>
                    <p className="text-lg font-bold text-slate-800">
                      {agendamentos.filter(a => a.status === 'confirmado').length}
                    </p>
                    <p className="text-xs text-slate-600">Confirmados</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="shadow-soft border-0">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-green-50 rounded-lg flex items-center justify-center">
                    <CheckCircle className="w-5 h-5 text-green-600" />
                  </div>
                  <div>
                    <p className="text-lg font-bold text-slate-800">
                      {agendamentos.filter(a => a.status === 'realizado').length}
                    </p>
                    <p className="text-xs text-slate-600">Realizados</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="shadow-soft border-0">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-red-50 rounded-lg flex items-center justify-center">
                    <XCircle className="w-5 h-5 text-red-600" />
                  </div>
                  <div>
                    <p className="text-lg font-bold text-slate-800">
                      {agendamentos.filter(a => a.status === 'cancelado').length}
                    </p>
                    <p className="text-xs text-slate-600">Cancelados</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Agendamentos List */}
          <div className="space-y-4">
            {datasSortidas.map((data) => (
              <div key={data}>
                <h3 className="text-lg font-semibold text-slate-800 mb-3">
                  {format(parseISO(data), "EEEE, dd 'de' MMMM", { locale: ptBR })}
                </h3>
                <div className="space-y-3">
                  {agendamentosPorData[data]
                    .sort((a, b) => new Date(a.data_hora).getTime() - new Date(b.data_hora).getTime())
                    .map((agendamento) => {
                      const cliente = clientes.find(c => c.id === agendamento.cliente_id);
                      const servico = servicos.find(s => s.id === agendamento.servico_id);
                      
                      return (
                        <Card key={agendamento.id} className="hover-lift shadow-soft border-0">
                          <CardContent className="p-4">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-4 flex-1">
                                <div className="text-center">
                                  <p className="text-lg font-bold text-slate-800">
                                    {format(new Date(agendamento.data_hora), 'HH:mm')}
                                  </p>
                                  <Badge className={`text-xs border ${getStatusColor(agendamento.status)}`}>
                                    {getStatusText(agendamento.status)}
                                  </Badge>
                                </div>
                                
                                <div className="flex-1">
                                  <div className="flex items-center gap-2 mb-1">
                                    <User className="w-4 h-4 text-slate-400" />
                                    <span className="font-semibold text-slate-800">{cliente?.nome}</span>
                                  </div>
                                  <div className="flex items-center gap-2 mb-1">
                                    <Wrench className="w-4 h-4 text-slate-400" />
                                    <span className="text-slate-600">{servico?.nome}</span>
                                    <span className="text-emerald-600 font-semibold">
                                      R$ {servico?.preco.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                                    </span>
                                  </div>
                                  {servico?.duracao_minutos && (
                                    <div className="flex items-center gap-2">
                                      <Clock className="w-4 h-4 text-slate-400" />
                                      <span className="text-sm text-slate-500">
                                        {servico.duracao_minutos}min
                                      </span>
                                    </div>
                                  )}
                                  {agendamento.observacoes && (
                                    <p className="text-sm text-slate-500 mt-1">{agendamento.observacoes}</p>
                                  )}
                                </div>
                              </div>
                              
                              <div className="flex gap-2">
                                {agendamento.status === 'confirmado' && (
                                  <Button
                                    size="sm"
                                    onClick={() => transformarEmVenda(agendamento)}
                                    className="bg-emerald-600 hover:bg-emerald-700"
                                  >
                                    <ShoppingCart className="w-4 h-4 mr-1" />
                                    Vender
                                  </Button>
                                )}
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => handleEdit(agendamento)}
                                >
                                  <Edit className="w-4 h-4" />
                                </Button>
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => handleDelete(agendamento.id)}
                                  className="text-red-500 hover:text-red-600"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      );
                    })}
                </div>
              </div>
            ))}
          </div>

          {filteredAgendamentos.length === 0 && (
            <div className="text-center py-12">
              <CalendarIcon className="w-16 h-16 mx-auto text-slate-400 mb-4" />
              <h3 className="text-lg font-semibold text-slate-600 mb-2">
                {busca ? 'Nenhum agendamento encontrado' : 'Nenhum agendamento cadastrado'}
              </h3>
              <p className="text-slate-500 mb-6">
                {busca 
                  ? 'Tente ajustar os termos de busca'
                  : 'Comece cadastrando seu primeiro agendamento'
                }
              </p>
              {!busca && (
                <Button onClick={() => setShowDialog(true)} className="bg-purple-600 hover:bg-purple-700">
                  <Plus className="w-4 h-4 mr-2" />
                  Novo Agendamento
                </Button>
              )}
            </div>
          )}
        </div>

        {/* Calendar Sidebar */}
        <div className="lg:col-span-1">
          <Card className="sticky top-6 shadow-soft border-0">
            <CardHeader>
              <CardTitle className="text-lg">Calendário</CardTitle>
            </CardHeader>
            <CardContent>
              <Calendar
                mode="single"
                selected={selectedDate}
                onSelect={setSelectedDate}
                locale={ptBR}
                className="rounded-md border-0"
              />
              <div className="mt-4 space-y-2">
                <div className="text-sm">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-3 h-3 bg-blue-200 rounded-full"></div>
                    <span>Agendado</span>
                  </div>
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-3 h-3 bg-emerald-200 rounded-full"></div>
                    <span>Confirmado</span>
                  </div>
                  <div className="flex items-center gap-2 mb-2">
                    <div className="w-3 h-3 bg-green-200 rounded-full"></div>
                    <span>Realizado</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 bg-red-200 rounded-full"></div>
                    <span>Cancelado</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default Agendamentos;