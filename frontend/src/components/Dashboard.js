import React, { useState, useEffect } from 'react';
import { useAuth } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { 
  DollarSign, 
  TrendingUp, 
  Package, 
  Calendar,
  ArrowUpRight,
  ArrowDownRight,
  Users,
  ShoppingCart
} from 'lucide-react';
import { toast } from 'sonner';

const Dashboard = () => {
  const { api } = useAuth();
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      const response = await api.get('/dashboard');
      setDashboard(response.data);
    } catch (error) {
      toast.error('Erro ao carregar dashboard');
      console.error('Error loading dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-6">
                <div className="h-20 bg-slate-200 rounded"></div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  const kpiCards = [
    {
      title: 'Total de Vendas',
      value: `R$ ${dashboard?.total_vendas?.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) || '0,00'}`,
      icon: DollarSign,
      change: '+12.5%',
      changeType: 'positive',
      color: 'emerald'
    },
    {
      title: 'Total de Despesas',
      value: `R$ ${dashboard?.total_despesas?.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) || '0,00'}`,
      icon: ArrowDownRight,
      change: '+8.2%',
      changeType: 'negative',
      color: 'red'
    },
    {
      title: 'Lucro',
      value: `R$ ${dashboard?.lucro?.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) || '0,00'}`,
      icon: TrendingUp,
      change: `${dashboard?.margem_lucro?.toFixed(1) || '0'}%`,
      changeType: 'positive',
      color: 'blue'
    },
    {
      title: 'Itens em Estoque',
      value: dashboard?.itens_estoque?.toLocaleString('pt-BR') || '0',
      icon: Package,
      change: '-2 itens',
      changeType: 'neutral',
      color: 'purple'
    }
  ];

  const colorClasses = {
    emerald: {
      bg: 'bg-emerald-50',
      icon: 'text-emerald-600',
      border: 'border-emerald-200'
    },
    red: {
      bg: 'bg-red-50',
      icon: 'text-red-600',
      border: 'border-red-200'
    },
    blue: {
      bg: 'bg-blue-50',
      icon: 'text-blue-600',
      border: 'border-blue-200'
    },
    purple: {
      bg: 'bg-purple-50',
      icon: 'text-purple-600',
      border: 'border-purple-200'
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-800">Dashboard</h1>
          <p className="text-slate-600 mt-1">Visão geral do seu negócio</p>
        </div>
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <Calendar className="w-4 h-4" />
          Atualizado em {new Date().toLocaleDateString('pt-BR')}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {kpiCards.map((kpi, index) => {
          const colors = colorClasses[kpi.color];
          return (
            <Card key={index} className="hover-lift cursor-pointer border-0 shadow-soft">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-slate-600 mb-1">{kpi.title}</p>
                    <p className="text-2xl font-bold text-slate-800 mb-2">{kpi.value}</p>
                    <div className="flex items-center gap-1">
                      {kpi.changeType === 'positive' && <ArrowUpRight className="w-4 h-4 text-emerald-600" />}
                      {kpi.changeType === 'negative' && <ArrowDownRight className="w-4 h-4 text-red-600" />}
                      <span className={`text-sm font-medium ${
                        kpi.changeType === 'positive' ? 'text-emerald-600' : 
                        kpi.changeType === 'negative' ? 'text-red-600' : 'text-slate-600'
                      }`}>
                        {kpi.change}
                      </span>
                    </div>
                  </div>
                  <div className={`w-12 h-12 rounded-xl ${colors.bg} ${colors.border} border flex items-center justify-center`}>
                    <kpi.icon className={`w-6 h-6 ${colors.icon}`} />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sales Chart */}
        <Card className="shadow-soft border-0">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-emerald-600" />
              Vendas por Período
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64 flex items-center justify-center bg-slate-50 rounded-lg">
              <div className="text-center text-slate-500">
                <BarChart3 className="w-12 h-12 mx-auto mb-3 text-slate-400" />
                <p>Gráfico de vendas será implementado</p>
                <p className="text-sm">com biblioteca de charts</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Top Products */}
        <Card className="shadow-soft border-0">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Package className="w-5 h-5 text-blue-600" />
              Top Produtos/Serviços
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {dashboard?.top_produtos?.map((produto, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                      <span className="text-sm font-bold text-blue-600">{index + 1}</span>
                    </div>
                    <div>
                      <p className="font-medium text-slate-800">{produto.nome}</p>
                      <p className="text-sm text-slate-500">{produto.vendas} vendas</p>
                    </div>
                  </div>
                  <ShoppingCart className="w-4 h-4 text-slate-400" />
                </div>
              )) || (
                <div className="text-center py-8 text-slate-500">
                  <Package className="w-12 h-12 mx-auto mb-3 text-slate-400" />
                  <p>Nenhum produto vendido ainda</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle>Ações Rápidas</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button className="p-4 bg-emerald-50 rounded-xl border border-emerald-200 hover:bg-emerald-100 transition-colors text-left group">
              <ShoppingCart className="w-8 h-8 text-emerald-600 mb-3 group-hover:scale-110 transition-transform" />
              <h3 className="font-semibold text-slate-800 mb-1">Nova Venda</h3>
              <p className="text-sm text-slate-600">Abrir PDV para nova venda</p>
            </button>

            <button className="p-4 bg-blue-50 rounded-xl border border-blue-200 hover:bg-blue-100 transition-colors text-left group">
              <Users className="w-8 h-8 text-blue-600 mb-3 group-hover:scale-110 transition-transform" />
              <h3 className="font-semibold text-slate-800 mb-1">Novo Cliente</h3>
              <p className="text-sm text-slate-600">Cadastrar novo cliente</p>
            </button>

            <button className="p-4 bg-purple-50 rounded-xl border border-purple-200 hover:bg-purple-100 transition-colors text-left group">
              <Calendar className="w-8 h-8 text-purple-600 mb-3 group-hover:scale-110 transition-transform" />
              <h3 className="font-semibold text-slate-800 mb-1">Agendamento</h3>
              <p className="text-sm text-slate-600">Novo agendamento</p>
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Dashboard;