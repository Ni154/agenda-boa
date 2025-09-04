import React, { useState, useEffect } from 'react';
import { useAuth } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { 
  Building2, 
  Users, 
  DollarSign, 
  TrendingUp,
  Plus,
  Eye,
  Ban,
  CheckCircle,
  XCircle,
  Clock,
  ArrowUpRight
} from 'lucide-react';
import { toast } from 'sonner';

const SuperAdminDashboard = () => {
  const { api } = useAuth();
  const [dashboard, setDashboard] = useState(null);
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateTenant, setShowCreateTenant] = useState(false);
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
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [dashboardRes, tenantsRes] = await Promise.all([
        api.get('/super-admin/dashboard'),
        api.get('/super-admin/tenants')
      ]);
      setDashboard(dashboardRes.data);
      setTenants(tenantsRes.data);
    } catch (error) {
      toast.error('Erro ao carregar dados do super admin');
      console.error('Error loading super admin data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTenant = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await api.post('/super-admin/tenants', formData);
      toast.success('Empresa criada com sucesso! Email de boas-vindas enviado.');
      setShowCreateTenant(false);
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
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Erro ao criar empresa');
    } finally {
      setLoading(false);
    }
  };

  const toggleTenantStatus = async (tenantId) => {
    try {
      await api.put(`/super-admin/tenants/${tenantId}/toggle-status`);
      toast.success('Status da empresa alterado com sucesso!');
      loadData();
    } catch (error) {
      toast.error('Erro ao alterar status da empresa');
    }
  };

  const getStatusColor = (tenant) => {
    if (!tenant.is_active) return 'bg-red-50 text-red-700 border-red-200';
    if (tenant.subscription_status === 'trial') return 'bg-yellow-50 text-yellow-700 border-yellow-200';
    return 'bg-emerald-50 text-emerald-700 border-emerald-200';
  };

  const getStatusText = (tenant) => {
    if (!tenant.is_active) return 'Suspensa';
    if (tenant.subscription_status === 'trial') return 'Trial';
    return 'Ativa';
  };

  const getStatusIcon = (tenant) => {
    if (!tenant.is_active) return <XCircle className="w-4 h-4" />;
    if (tenant.subscription_status === 'trial') return <Clock className="w-4 h-4" />;
    return <CheckCircle className="w-4 h-4" />;
  };

  const handleChange = (e) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  if (loading && !dashboard) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-slate-200 rounded w-1/4 mb-4"></div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-32 bg-slate-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-800">Super Admin Dashboard</h1>
          <p className="text-slate-600 mt-1">Gerencie todas as empresas do sistema SaaS</p>
        </div>
        <Dialog open={showCreateTenant} onOpenChange={setShowCreateTenant}>
          <DialogTrigger asChild>
            <Button className="bg-emerald-600 hover:bg-emerald-700">
              <Plus className="w-4 h-4 mr-2" />
              Nova Empresa
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Criar Nova Empresa</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreateTenant} className="space-y-4">
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
                    placeholder="Minha Empresa LTDA"
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
                    placeholder="00.000.000/0001-00"
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
                <h3 className="text-lg font-semibold text-slate-800 mb-3">Administrador da Empresa</h3>
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
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                  <div>
                    <Label htmlFor="admin_password">Senha Inicial *</Label>
                    <Input
                      id="admin_password"
                      name="admin_password"
                      type="password"
                      required
                      value={formData.admin_password}
                      onChange={handleChange}
                      placeholder="••••••••"
                    />
                  </div>
                  <div>
                    <Label htmlFor="plan">Plano</Label>
                    <Select onValueChange={(value) => setFormData(prev => ({...prev, plan: value}))} value={formData.plan}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="basic">Basic</SelectItem>
                        <SelectItem value="premium">Premium</SelectItem>
                        <SelectItem value="enterprise">Enterprise</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              <div className="flex gap-3 pt-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowCreateTenant(false)}
                  className="flex-1"
                >
                  Cancelar
                </Button>
                <Button
                  type="submit"
                  disabled={loading}
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700"
                >
                  {loading ? 'Criando...' : 'Criar Empresa'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="hover-lift cursor-pointer shadow-soft border-0">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-600 mb-1">Total de Empresas</p>
                <p className="text-2xl font-bold text-slate-800">{dashboard?.total_tenants || 0}</p>
                <p className="text-sm text-emerald-600 flex items-center gap-1">
                  <ArrowUpRight className="w-3 h-3" />
                  +{dashboard?.recent_signups?.length || 0} este mês
                </p>
              </div>
              <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center border border-blue-200">
                <Building2 className="w-6 h-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="hover-lift cursor-pointer shadow-soft border-0">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-600 mb-1">Empresas Ativas</p>
                <p className="text-2xl font-bold text-slate-800">{dashboard?.active_tenants || 0}</p>
                <p className="text-sm text-emerald-600">
                  {dashboard?.total_tenants > 0 ? Math.round((dashboard.active_tenants / dashboard.total_tenants) * 100) : 0}% do total
                </p>
              </div>
              <div className="w-12 h-12 bg-emerald-50 rounded-xl flex items-center justify-center border border-emerald-200">
                <CheckCircle className="w-6 h-6 text-emerald-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="hover-lift cursor-pointer shadow-soft border-0">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-600 mb-1">Em Trial</p>
                <p className="text-2xl font-bold text-slate-800">{dashboard?.trial_tenants || 0}</p>
                <p className="text-sm text-yellow-600">Potenciais conversões</p>
              </div>
              <div className="w-12 h-12 bg-yellow-50 rounded-xl flex items-center justify-center border border-yellow-200">
                <Clock className="w-6 h-6 text-yellow-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="hover-lift cursor-pointer shadow-soft border-0">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-600 mb-1">Total de Usuários</p>
                <p className="text-2xl font-bold text-slate-800">{dashboard?.total_users || 0}</p>
                <p className="text-sm text-slate-500">Todos os tenants</p>
              </div>
              <div className="w-12 h-12 bg-purple-50 rounded-xl flex items-center justify-center border border-purple-200">
                <Users className="w-6 h-6 text-purple-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tenants Table */}
      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle>Empresas Cadastradas</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {tenants.map((tenant) => (
              <div key={tenant.id} className="flex items-center justify-between p-4 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-emerald-100 rounded-lg flex items-center justify-center">
                    <Building2 className="w-6 h-6 text-emerald-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-800">{tenant.company_name}</h3>
                    <p className="text-sm text-slate-500">
                      {tenant.subdomain} • {tenant.cnpj || 'CNPJ não informado'}
                    </p>
                    <p className="text-xs text-slate-400">
                      Criada em {new Date(tenant.created_at).toLocaleDateString('pt-BR')}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Badge className={`border ${getStatusColor(tenant)}`}>
                    {getStatusIcon(tenant)}
                    <span className="ml-1">{getStatusText(tenant)}</span>
                  </Badge>
                  <Badge variant="outline" className="text-blue-600">
                    {tenant.plan}
                  </Badge>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => toggleTenantStatus(tenant.id)}
                    className={tenant.is_active ? 'text-red-600 hover:text-red-700' : 'text-emerald-600 hover:text-emerald-700'}
                  >
                    {tenant.is_active ? (
                      <>
                        <Ban className="w-4 h-4 mr-1" />
                        Suspender
                      </>
                    ) : (
                      <>
                        <CheckCircle className="w-4 h-4 mr-1" />
                        Ativar
                      </>
                    )}
                  </Button>
                </div>
              </div>
            ))}
            
            {tenants.length === 0 && (
              <div className="text-center py-12">
                <Building2 className="w-16 h-16 mx-auto text-slate-400 mb-4" />
                <h3 className="text-lg font-semibold text-slate-600 mb-2">Nenhuma empresa cadastrada</h3>
                <p className="text-slate-500 mb-6">Comece criando sua primeira empresa</p>
                <Button onClick={() => setShowCreateTenant(true)} className="bg-emerald-600 hover:bg-emerald-700">
                  <Plus className="w-4 h-4 mr-2" />
                  Criar Primeira Empresa
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default SuperAdminDashboard;