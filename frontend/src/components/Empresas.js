import React, { useState, useEffect } from 'react';
import { useAuth } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
import { Badge } from './ui/badge';
import { 
  Building2, 
  Plus, 
  Search, 
  Edit, 
  Trash2, 
  Shield,
  Clock,
  Users,
  CreditCard
} from 'lucide-react';
import { toast } from 'sonner';

const Empresas = () => {
  const { api, user } = useAuth();
  const [empresas, setEmpresas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busca, setBusca] = useState('');
  const [showDialog, setShowDialog] = useState(false);
  const [editingEmpresa, setEditingEmpresa] = useState(null);
  const [formData, setFormData] = useState({
    subdomain: '',
    company_name: '',
    cnpj: '',
    razao_social: '',
    admin_name: '',
    admin_email: '',
    admin_password: '',
    plan: 'basic'
  });

  useEffect(() => {
    if (user?.role === 'super_admin') {
      loadEmpresas();
    }
  }, [user]);

  const loadEmpresas = async () => {
    try {
      const response = await api.get('/super-admin/tenants');
      setEmpresas(response.data);
    } catch (error) {
      toast.error('Erro ao carregar empresas');
      console.error('Error loading empresas:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (editingEmpresa) {
        // Edit functionality would go here
        toast.success('Empresa atualizada com sucesso!');
      } else {
        await api.post('/super-admin/tenants', formData);
        toast.success('Empresa cadastrada com sucesso!');
      }
      
      setShowDialog(false);
      resetForm();
      loadEmpresas();
    } catch (error) {
      toast.error('Erro ao salvar empresa');
      console.error('Error saving empresa:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleStatus = async (empresaId) => {
    try {
      await api.put(`/super-admin/tenants/${empresaId}/toggle-status`);
      toast.success('Status da empresa alterado com sucesso!');
      loadEmpresas();
    } catch (error) {
      toast.error('Erro ao alterar status da empresa');
      console.error('Error toggling status:', error);
    }
  };

  const resetForm = () => {
    setFormData({
      subdomain: '',
      company_name: '',
      cnpj: '',
      razao_social: '',
      admin_name: '',
      admin_email: '',
      admin_password: '',
      plan: 'basic'
    });
    setEditingEmpresa(null);
  };

  const handleChange = (e) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  const filteredEmpresas = empresas.filter(empresa =>
    empresa.company_name.toLowerCase().includes(busca.toLowerCase()) ||
    empresa.subdomain.toLowerCase().includes(busca.toLowerCase()) ||
    (empresa.cnpj && empresa.cnpj.includes(busca))
  );

  const getStatusColor = (isActive) => {
    return isActive ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-red-50 text-red-700 border-red-200';
  };

  const getStatusText = (isActive) => {
    return isActive ? 'Ativa' : 'Suspensa';
  };

  const getPlanColor = (plan) => {
    switch (plan) {
      case 'premium': return 'bg-purple-50 text-purple-700 border-purple-200';
      case 'enterprise': return 'bg-blue-50 text-blue-700 border-blue-200';
      default: return 'bg-slate-50 text-slate-700 border-slate-200';
    }
  };

  if (user?.role !== 'super_admin') {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Shield className="w-16 h-16 mx-auto text-slate-400 mb-4" />
          <h3 className="text-lg font-semibold text-slate-600 mb-2">
            Acesso Restrito
          </h3>
          <p className="text-slate-500">
            Apenas super administradores podem acessar esta página
          </p>
        </div>
      </div>
    );
  }

  if (loading && empresas.length === 0) {
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
          <h1 className="text-3xl font-bold text-slate-800">Empresas</h1>
          <p className="text-slate-600 mt-1">Gerencie as empresas do sistema</p>
        </div>
        <Dialog open={showDialog} onOpenChange={setShowDialog}>
          <DialogTrigger asChild>
            <Button onClick={resetForm} className="bg-emerald-600 hover:bg-emerald-700">
              <Plus className="w-4 h-4 mr-2" />
              Nova Empresa
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>
                {editingEmpresa ? 'Editar Empresa' : 'Nova Empresa'}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="subdomain">Subdomínio *</Label>
                  <Input
                    id="subdomain"
                    name="subdomain"
                    required
                    value={formData.subdomain}
                    onChange={handleChange}
                    placeholder="minha-empresa"
                  />
                  <p className="text-xs text-slate-500 mt-1">
                    Será usado como: minha-empresa.sistema.com
                  </p>
                </div>
                <div>
                  <Label htmlFor="company_name">Nome da Empresa *</Label>
                  <Input
                    id="company_name"
                    name="company_name"
                    required
                    value={formData.company_name}
                    onChange={handleChange}
                    placeholder="Nome da empresa"
                  />
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="cnpj">CNPJ</Label>
                  <Input
                    id="cnpj"
                    name="cnpj"
                    value={formData.cnpj}
                    onChange={handleChange}
                    placeholder="00.000.000/0000-00"
                  />
                </div>
                <div>
                  <Label htmlFor="razao_social">Razão Social</Label>
                  <Input
                    id="razao_social"
                    name="razao_social"
                    value={formData.razao_social}
                    onChange={handleChange}
                    placeholder="Razão social da empresa"
                  />
                </div>
              </div>

              <div className="border-t pt-4">
                <h4 className="font-semibold text-slate-700 mb-3">Administrador da Empresa</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="admin_name">Nome do Admin *</Label>
                    <Input
                      id="admin_name"
                      name="admin_name"
                      required
                      value={formData.admin_name}
                      onChange={handleChange}
                      placeholder="Nome do administrador"
                    />
                  </div>
                  <div>
                    <Label htmlFor="admin_email">Email do Admin *</Label>
                    <Input
                      id="admin_email"
                      name="admin_email"
                      type="email"
                      required
                      value={formData.admin_email}
                      onChange={handleChange}
                      placeholder="admin@empresa.com"
                    />
                  </div>
                </div>
                <div className="mt-4">
                  <Label htmlFor="admin_password">Senha do Admin *</Label>
                  <Input
                    id="admin_password"
                    name="admin_password"
                    type="password"
                    required
                    value={formData.admin_password}
                    onChange={handleChange}
                    placeholder="Senha segura"
                    minLength={6}
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="plan">Plano</Label>
                <select
                  id="plan"
                  name="plan"
                  value={formData.plan}
                  onChange={handleChange}
                  className="w-full p-2 border border-slate-300 rounded-md"
                >
                  <option value="basic">Básico</option>
                  <option value="premium">Premium</option>
                  <option value="enterprise">Enterprise</option>
                </select>
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
                  {loading ? 'Salvando...' : editingEmpresa ? 'Atualizar' : 'Cadastrar'}
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
              placeholder="Buscar empresas por nome, subdomínio ou CNPJ..."
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
                <Building2 className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-800">{empresas.length}</p>
                <p className="text-sm text-slate-600">Total de Empresas</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="shadow-soft border-0">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-emerald-50 rounded-xl flex items-center justify-center border border-emerald-200">
                <Shield className="w-6 h-6 text-emerald-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-800">
                  {empresas.filter(e => e.is_active).length}
                </p>
                <p className="text-sm text-slate-600">Empresas Ativas</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="shadow-soft border-0">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-yellow-50 rounded-xl flex items-center justify-center border border-yellow-200">
                <Clock className="w-6 h-6 text-yellow-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-800">
                  {empresas.filter(e => e.subscription_status === 'trial').length}
                </p>
                <p className="text-sm text-slate-600">Em Trial</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-soft border-0">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-purple-50 rounded-xl flex items-center justify-center border border-purple-200">
                <CreditCard className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-800">
                  {empresas.filter(e => e.plan === 'premium' || e.plan === 'enterprise').length}
                </p>
                <p className="text-sm text-slate-600">Planos Pagos</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Empresas Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredEmpresas.map((empresa) => (
          <Card key={empresa.id} className="hover-lift shadow-soft border-0">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                    <Building2 className="w-5 h-5 text-blue-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-lg truncate">{empresa.company_name}</CardTitle>
                    <p className="text-sm text-slate-500">{empresa.subdomain}</p>
                  </div>
                </div>
                <div className="flex gap-1">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleToggleStatus(empresa.id)}
                    className="h-8 w-8 p-0"
                  >
                    <Shield className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            
            <CardContent>
              <div className="space-y-3">
                {empresa.cnpj && (
                  <p className="text-sm text-slate-600">CNPJ: {empresa.cnpj}</p>
                )}
                
                <div className="flex justify-between items-center">
                  <Badge className={`border ${getStatusColor(empresa.is_active)}`}>
                    {getStatusText(empresa.is_active)}
                  </Badge>
                  <Badge className={`border ${getPlanColor(empresa.plan)}`}>
                    {empresa.plan.charAt(0).toUpperCase() + empresa.plan.slice(1)}
                  </Badge>
                </div>

                <div className="text-xs text-slate-500">
                  Criada em: {new Date(empresa.created_at).toLocaleDateString('pt-BR')}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredEmpresas.length === 0 && (
        <div className="text-center py-12">
          <Building2 className="w-16 h-16 mx-auto text-slate-400 mb-4" />
          <h3 className="text-lg font-semibold text-slate-600 mb-2">
            {busca ? 'Nenhuma empresa encontrada' : 'Nenhuma empresa cadastrada'}
          </h3>
          <p className="text-slate-500 mb-6">
            {busca 
              ? 'Tente ajustar os termos de busca'
              : 'Comece cadastrando a primeira empresa'
            }
          </p>
          {!busca && (
            <Button onClick={() => setShowDialog(true)} className="bg-emerald-600 hover:bg-emerald-700">
              <Plus className="w-4 h-4 mr-2" />
              Cadastrar Empresa
            </Button>
          )}
        </div>
      )}
    </div>
  );
};

export default Empresas;