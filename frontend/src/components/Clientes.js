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
  Users, 
  Plus, 
  Search, 
  Edit, 
  Trash2, 
  Phone, 
  Mail, 
  MapPin,
  User,
  Camera,
  Image
} from 'lucide-react';
import { toast } from 'sonner';

const Clientes = () => {
  const { api } = useAuth();
  const [clientes, setClientes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busca, setBusca] = useState('');
  const [showDialog, setShowDialog] = useState(false);
  const [editingCliente, setEditingCliente] = useState(null);
  const [formData, setFormData] = useState({
    nome: '',
    email: '',
    telefone: '',
    cpf_cnpj: '',
    endereco: '',
    anamnese: ''
  });

  useEffect(() => {
    loadClientes();
  }, []);

  const loadClientes = async () => {
    try {
      const response = await api.get('/clientes');
      setClientes(response.data);
    } catch (error) {
      toast.error('Erro ao carregar clientes');
      console.error('Error loading clientes:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (editingCliente) {
        await api.put(`/clientes/${editingCliente.id}`, formData);
        toast.success('Cliente atualizado com sucesso!');
      } else {
        await api.post('/clientes', formData);
        toast.success('Cliente cadastrado com sucesso!');
      }
      
      setShowDialog(false);
      resetForm();
      loadClientes();
    } catch (error) {
      toast.error('Erro ao salvar cliente');
      console.error('Error saving cliente:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (cliente) => {
    setEditingCliente(cliente);
    setFormData({
      nome: cliente.nome || '',
      email: cliente.email || '',
      telefone: cliente.telefone || '',
      cpf_cnpj: cliente.cpf_cnpj || '',
      endereco: cliente.endereco || '',
      anamnese: cliente.anamnese || ''
    });
    setShowDialog(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Tem certeza que deseja excluir este cliente?')) return;

    try {
      await api.delete(`/clientes/${id}`);
      toast.success('Cliente excluído com sucesso!');
      loadClientes();
    } catch (error) {
      toast.error('Erro ao excluir cliente');
      console.error('Error deleting cliente:', error);
    }
  };

  const resetForm = () => {
    setFormData({
      nome: '',
      email: '',
      telefone: '',
      cpf_cnpj: '',
      endereco: '',
      anamnese: ''
    });
    setEditingCliente(null);
  };

  const handleChange = (e) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  const filteredClientes = clientes.filter(cliente =>
    cliente.nome.toLowerCase().includes(busca.toLowerCase()) ||
    (cliente.email && cliente.email.toLowerCase().includes(busca.toLowerCase())) ||
    (cliente.cpf_cnpj && cliente.cpf_cnpj.includes(busca))
  );

  const handleTakePhoto = () => {
    // Request camera permission explicitly
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
          // Stop the stream immediately since we just wanted permission
          stream.getTracks().forEach(track => track.stop());
          toast.success('Câmera autorizada! Funcionalidade será implementada.');
        })
        .catch(err => {
          toast.error('Permissão de câmera negada ou não disponível.');
          console.error('Camera permission denied:', err);
        });
    } else {
      toast.error('Câmera não disponível neste dispositivo.');
    }
  };

  if (loading && clientes.length === 0) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-slate-200 rounded w-1/4 mb-4"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="h-32 bg-slate-200 rounded"></div>
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
          <h1 className="text-3xl font-bold text-slate-800">Clientes</h1>
          <p className="text-slate-600 mt-1">Gerencie sua base de clientes</p>
        </div>
        <Dialog open={showDialog} onOpenChange={setShowDialog}>
          <DialogTrigger asChild>
            <Button onClick={resetForm} className="bg-emerald-600 hover:bg-emerald-700">
              <Plus className="w-4 h-4 mr-2" />
              Novo Cliente
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                {editingCliente ? 'Editar Cliente' : 'Novo Cliente'}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="nome">Nome *</Label>
                  <Input
                    id="nome"
                    name="nome"
                    required
                    value={formData.nome}
                    onChange={handleChange}
                    placeholder="Nome completo"
                  />
                </div>
                <div>
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    value={formData.email}
                    onChange={handleChange}
                    placeholder="email@exemplo.com"
                  />
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="telefone">Telefone</Label>
                  <Input
                    id="telefone"
                    name="telefone"
                    value={formData.telefone}
                    onChange={handleChange}
                    placeholder="(11) 99999-9999"
                  />
                </div>
                <div>
                  <Label htmlFor="cpf_cnpj">CPF/CNPJ</Label>
                  <Input
                    id="cpf_cnpj"
                    name="cpf_cnpj"
                    value={formData.cpf_cnpj}
                    onChange={handleChange}
                    placeholder="000.000.000-00"
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="endereco">Endereço</Label>
                <Input
                  id="endereco"
                  name="endereco"
                  value={formData.endereco}
                  onChange={handleChange}
                  placeholder="Endereço completo"
                />
              </div>

              <div>
                <Label htmlFor="anamnese">Ficha de Análise/Anamnese</Label>
                <Textarea
                  id="anamnese"
                  name="anamnese"
                  value={formData.anamnese}
                  onChange={handleChange}
                  placeholder="Informações importantes sobre o cliente..."
                  rows={4}
                />
              </div>

              {/* Photo Section */}
              <div>
                <Label>Foto do Cliente</Label>
                <div className="flex gap-3 mt-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleTakePhoto}
                    className="flex items-center gap-2"
                  >
                    <Camera className="w-4 h-4" />
                    Tirar Foto
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    className="flex items-center gap-2"
                  >
                    <Image className="w-4 h-4" />
                    Anexar Imagem
                  </Button>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  A câmera só será ativada após clique e permissão explícita
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
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700"
                >
                  {loading ? 'Salvando...' : editingCliente ? 'Atualizar' : 'Cadastrar'}
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
              placeholder="Buscar clientes por nome, email ou CPF/CNPJ..."
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
              <div className="w-12 h-12 bg-emerald-50 rounded-xl flex items-center justify-center border border-emerald-200">
                <Users className="w-6 h-6 text-emerald-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-800">{clientes.length}</p>
                <p className="text-sm text-slate-600">Total de Clientes</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="shadow-soft border-0">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center border border-blue-200">
                <Mail className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-800">
                  {clientes.filter(c => c.email).length}
                </p>
                <p className="text-sm text-slate-600">Com Email</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="shadow-soft border-0">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-purple-50 rounded-xl flex items-center justify-center border border-purple-200">
                <Phone className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-800">
                  {clientes.filter(c => c.telefone).length}
                </p>
                <p className="text-sm text-slate-600">Com Telefone</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Clientes Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredClientes.map((cliente) => (
          <Card key={cliente.id} className="hover-lift shadow-soft border-0">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-emerald-100 rounded-full flex items-center justify-center">
                    {cliente.foto_url ? (
                      <img src={cliente.foto_url} alt={cliente.nome} className="w-10 h-10 rounded-full object-cover" />
                    ) : (
                      <User className="w-5 h-5 text-emerald-600" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-lg truncate">{cliente.nome}</CardTitle>
                    {cliente.cpf_cnpj && (
                      <p className="text-sm text-slate-500">{cliente.cpf_cnpj}</p>
                    )}
                  </div>
                </div>
                <div className="flex gap-1">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleEdit(cliente)}
                    className="h-8 w-8 p-0"
                  >
                    <Edit className="w-4 h-4" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleDelete(cliente.id)}
                    className="h-8 w-8 p-0 text-red-500 hover:text-red-600"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {cliente.email && (
                  <div className="flex items-center gap-2 text-sm text-slate-600">
                    <Mail className="w-4 h-4" />
                    <span className="truncate">{cliente.email}</span>
                  </div>
                )}
                {cliente.telefone && (
                  <div className="flex items-center gap-2 text-sm text-slate-600">
                    <Phone className="w-4 h-4" />
                    <span>{cliente.telefone}</span>
                  </div>
                )}
                {cliente.endereco && (
                  <div className="flex items-center gap-2 text-sm text-slate-600">
                    <MapPin className="w-4 h-4" />
                    <span className="truncate">{cliente.endereco}</span>
                  </div>
                )}
                {cliente.anamnese && (
                  <div className="mt-3 pt-3 border-t border-slate-100">
                    <Badge variant="outline" className="text-xs">
                      Com Anamnese
                    </Badge>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredClientes.length === 0 && (
        <div className="text-center py-12">
          <Users className="w-16 h-16 mx-auto text-slate-400 mb-4" />
          <h3 className="text-lg font-semibold text-slate-600 mb-2">
            {busca ? 'Nenhum cliente encontrado' : 'Nenhum cliente cadastrado'}
          </h3>
          <p className="text-slate-500 mb-6">
            {busca 
              ? 'Tente ajustar os termos de busca'
              : 'Comece cadastrando seu primeiro cliente'
            }
          </p>
          {!busca && (
            <Button onClick={() => setShowDialog(true)} className="bg-emerald-600 hover:bg-emerald-700">
              <Plus className="w-4 h-4 mr-2" />
              Cadastrar Cliente
            </Button>
          )}
        </div>
      )}
    </div>
  );
};

export default Clientes;