import React, { useState, useEffect } from 'react';
import { useAuth } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
import { Badge } from './ui/badge';
import { 
  Users, 
  Plus, 
  Search, 
  Edit, 
  Trash2, 
  Shield,
  ShieldCheck,
  UserX,
  UserCheck,
  Mail,
  User
} from 'lucide-react';
import { toast } from 'sonner';

const Usuarios = () => {
  const { api, user } = useAuth();
  const [usuarios, setUsuarios] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busca, setBusca] = useState('');
  const [showDialog, setShowDialog] = useState(false);
  const [editingUsuario, setEditingUsuario] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    role: 'operador'
  });

  useEffect(() => {
    if (user?.role === 'super_admin' || user?.role === 'admin_empresa') {
      loadUsuarios();
    }
  }, [user]);

  const loadUsuarios = async () => {
    try {
      const response = await api.get('/users');
      setUsuarios(response.data);
    } catch (error) {
      toast.error('Erro ao carregar usuários');
      console.error('Error loading usuarios:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (editingUsuario) {
        await api.put(`/users/${editingUsuario.id}`, formData);
        toast.success('Usuário atualizado com sucesso!');
      } else {
        await api.post('/users', formData);
        toast.success('Usuário cadastrado com sucesso!');
      }
      
      setShowDialog(false);
      resetForm();
      loadUsuarios();
    } catch (error) {
      toast.error('Erro ao salvar usuário');
      console.error('Error saving usuario:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = (usuario) => {
    setEditingUsuario(usuario);
    setFormData({
      name: usuario.name || '',
      email: usuario.email || '',
      password: '', // Don't pre-fill password
      role: usuario.role || 'operador'
    });
    setShowDialog(true);
  };

  const handleToggleStatus = async (usuarioId) => {
    try {
      await api.put(`/users/${usuarioId}/toggle-status`);
      toast.success('Status do usuário alterado com sucesso!');
      loadUsuarios();
    } catch (error) {
      toast.error('Erro ao alterar status do usuário');
      console.error('Error toggling status:', error);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Tem certeza que deseja excluir este usuário?')) return;

    try {
      await api.delete(`/users/${id}`);
      toast.success('Usuário excluído com sucesso!');
      loadUsuarios();
    } catch (error) {
      toast.error('Erro ao excluir usuário');
      console.error('Error deleting usuario:', error);
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      email: '',
      password: '',
      role: 'operador'
    });
    setEditingUsuario(null);
  };

  const handleChange = (e) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  const filteredUsuarios = usuarios.filter(usuario =>
    usuario.name.toLowerCase().includes(busca.toLowerCase()) ||
    usuario.email.toLowerCase().includes(busca.toLowerCase()) ||
    usuario.role.toLowerCase().includes(busca.toLowerCase())
  );

  const getRoleColor = (role) => {
    switch (role) {
      case 'super_admin': return 'bg-red-50 text-red-700 border-red-200';
      case 'admin_empresa': return 'bg-purple-50 text-purple-700 border-purple-200';
      case 'operador': return 'bg-blue-50 text-blue-700 border-blue-200';
      default: return 'bg-slate-50 text-slate-700 border-slate-200';
    }
  };

  const getRoleText = (role) => {
    switch (role) {
      case 'super_admin': return 'Super Admin';
      case 'admin_empresa': return 'Admin Empresa';
      case 'operador': return 'Operador';
      default: return role;
    }
  };

  const getStatusColor = (isActive) => {
    return isActive ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-red-50 text-red-700 border-red-200';
  };

  const getStatusText = (isActive) => {
    return isActive ? 'Ativo' : 'Inativo';
  };

  if (user?.role !== 'super_admin' && user?.role !== 'admin_empresa') {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Shield className="w-16 h-16 mx-auto text-slate-400 mb-4" />
          <h3 className="text-lg font-semibold text-slate-600 mb-2">
            Acesso Restrito
          </h3>
          <p className="text-slate-500">
            Apenas administradores podem acessar esta página
          </p>
        </div>
      </div>
    );
  }

  if (loading && usuarios.length === 0) {
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
          <h1 className="text-3xl font-bold text-slate-800">Usuários</h1>
          <p className="text-slate-600 mt-1">Gerencie os usuários do sistema</p>
        </div>
        <Dialog open={showDialog} onOpenChange={setShowDialog}>
          <DialogTrigger asChild>
            <Button onClick={resetForm} className="bg-emerald-600 hover:bg-emerald-700">
              <Plus className="w-4 h-4 mr-2" />
              Novo Usuário
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle>
                {editingUsuario ? 'Editar Usuário' : 'Novo Usuário'}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label htmlFor="name">Nome *</Label>
                <Input
                  id="name"
                  name="name"
                  required
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="Nome completo"
                />
              </div>
              
              <div>
                <Label htmlFor="email">Email *</Label>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  required
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="email@exemplo.com"
                />
              </div>

              <div>
                <Label htmlFor="password">
                  {editingUsuario ? 'Nova Senha (deixe vazio para manter)' : 'Senha *'}
                </Label>
                <Input
                  id="password"
                  name="password"
                  type="password"
                  required={!editingUsuario}
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="Senha segura"
                  minLength={6}
                />
              </div>

              <div>
                <Label htmlFor="role">Função</Label>
                <select
                  id="role"
                  name="role"
                  value={formData.role}
                  onChange={handleChange}
                  className="w-full p-2 border border-slate-300 rounded-md"
                >
                  <option value="operador">Operador</option>
                  {user?.role === 'super_admin' && (
                    <>
                      <option value="admin_empresa">Admin Empresa</option>
                      <option value="super_admin">Super Admin</option>
                    </>
                  )}
                  {user?.role === 'admin_empresa' && (
                    <option value="admin_empresa">Admin Empresa</option>
                  )}
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
                  {loading ? 'Salvando...' : editingUsuario ? 'Atualizar' : 'Cadastrar'}
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
              placeholder="Buscar usuários por nome, email ou função..."
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
                <Users className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-800">{usuarios.length}</p>
                <p className="text-sm text-slate-600">Total de Usuários</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="shadow-soft border-0">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-emerald-50 rounded-xl flex items-center justify-center border border-emerald-200">
                <UserCheck className="w-6 h-6 text-emerald-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-800">
                  {usuarios.filter(u => u.is_active).length}
                </p>
                <p className="text-sm text-slate-600">Usuários Ativos</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="shadow-soft border-0">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-purple-50 rounded-xl flex items-center justify-center border border-purple-200">
                <ShieldCheck className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-800">
                  {usuarios.filter(u => u.role === 'admin_empresa').length}
                </p>
                <p className="text-sm text-slate-600">Administradores</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-soft border-0">
          <CardContent className="p-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-red-50 rounded-xl flex items-center justify-center border border-red-200">
                <UserX className="w-6 h-6 text-red-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-800">
                  {usuarios.filter(u => !u.is_active).length}
                </p>
                <p className="text-sm text-slate-600">Usuários Inativos</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Usuarios Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredUsuarios.map((usuario) => (
          <Card key={usuario.id} className="hover-lift shadow-soft border-0">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                    <User className="w-5 h-5 text-blue-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-lg truncate">{usuario.name}</CardTitle>
                    <div className="flex items-center gap-2 text-sm text-slate-500">
                      <Mail className="w-3 h-3" />
                      <span className="truncate">{usuario.email}</span>
                    </div>
                  </div>
                </div>
                <div className="flex gap-1">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleEdit(usuario)}
                    className="h-8 w-8 p-0"
                  >
                    <Edit className="w-4 h-4" />
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleToggleStatus(usuario.id)}
                    className="h-8 w-8 p-0"
                    title={usuario.is_active ? "Desativar usuário" : "Ativar usuário"}
                  >
                    {usuario.is_active ? (
                      <UserX className="w-4 h-4 text-yellow-600" />
                    ) : (
                      <UserCheck className="w-4 h-4 text-emerald-600" />
                    )}
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleDelete(usuario.id)}
                    className="h-8 w-8 p-0 text-red-500 hover:text-red-600"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            
            <CardContent>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <Badge className={`border ${getRoleColor(usuario.role)}`}>
                    {getRoleText(usuario.role)}
                  </Badge>
                  <Badge className={`border ${getStatusColor(usuario.is_active)}`}>
                    {getStatusText(usuario.is_active)}
                  </Badge>
                </div>

                {usuario.tenant_id && (
                  <div className="text-xs text-slate-500">
                    ID Empresa: {usuario.tenant_id.substring(0, 8)}...
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredUsuarios.length === 0 && (
        <div className="text-center py-12">
          <Users className="w-16 h-16 mx-auto text-slate-400 mb-4" />
          <h3 className="text-lg font-semibold text-slate-600 mb-2">
            {busca ? 'Nenhum usuário encontrado' : 'Nenhum usuário cadastrado'}
          </h3>
          <p className="text-slate-500 mb-6">
            {busca 
              ? 'Tente ajustar os termos de busca'
              : 'Comece cadastrando o primeiro usuário'
            }
          </p>
          {!busca && (
            <Button onClick={() => setShowDialog(true)} className="bg-emerald-600 hover:bg-emerald-700">
              <Plus className="w-4 h-4 mr-2" />
              Cadastrar Usuário
            </Button>
          )}
        </div>
      )}
    </div>
  );
};

export default Usuarios;