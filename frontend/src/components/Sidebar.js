import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../App';
import { Button } from './ui/button';
import { 
  LayoutDashboard, 
  ShoppingCart, 
  Calendar, 
  Package, 
  DollarSign, 
  BarChart3, 
  Users, 
  ChevronDown,
  Settings,
  LogOut,
  Building2,
  UserPlus,
  Wrench,
  Archive
} from 'lucide-react';

const Sidebar = ({ isOpen, setIsOpen }) => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [cadastroOpen, setCadastroOpen] = useState(false);

  const menuItems = [
    { icon: LayoutDashboard, label: 'Dashboard', path: '/' },
    { icon: ShoppingCart, label: 'POS/Vendas', path: '/pos' },
    { icon: Calendar, label: 'Agendamentos', path: '/agendamentos' },
    { icon: Package, label: 'Estoque', path: '/estoque' },
    { icon: DollarSign, label: 'Financeiro', path: '/financeiro' },
    { icon: BarChart3, label: 'Relatórios', path: '/relatorios' },
    { icon: Users, label: 'Usuários', path: '/usuarios' },
  ];

  const cadastroItems = [
    { icon: Users, label: 'Clientes', path: '/clientes' },
    { icon: Building2, label: 'Fornecedores', path: '/fornecedores' },
    { icon: Wrench, label: 'Serviços', path: '/servicos' },
    { icon: Package, label: 'Produtos', path: '/produtos' },
  ];

  const isActive = (path) => location.pathname === path;

  const handleLogout = () => {
    logout();
    setIsOpen(false);
  };

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setIsOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`
        fixed top-0 left-0 z-50 h-full w-80 bg-white shadow-2xl transform transition-transform duration-300 ease-in-out
        lg:relative lg:translate-x-0 lg:shadow-none lg:border-r lg:border-slate-200
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        {/* Header */}
        <div className="p-6 border-b border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-xl flex items-center justify-center">
              <Building2 className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="font-bold text-slate-800">ERP Sistema</h2>
              <p className="text-sm text-slate-500">Gestão Empresarial</p>
            </div>
          </div>
        </div>

        {/* User info */}
        <div className="p-4 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-emerald-100 rounded-full flex items-center justify-center">
              <UserPlus className="w-4 h-4 text-emerald-600" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-slate-800 truncate">{user?.name}</p>
              <p className="text-xs text-slate-500 truncate">{user?.email}</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto p-4">
          <div className="space-y-2">
            {menuItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setIsOpen(false)}
                className={`
                  flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200
                  ${isActive(item.path) 
                    ? 'bg-emerald-50 text-emerald-700 shadow-sm' 
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                  }
                `}
              >
                <item.icon className="w-5 h-5" />
                {item.label}
              </Link>
            ))}

            {/* Cadastro Dropdown */}
            <div>
              <button
                onClick={() => setCadastroOpen(!cadastroOpen)}
                className={`
                  w-full flex items-center justify-between gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200
                  ${cadastroItems.some(item => isActive(item.path))
                    ? 'bg-emerald-50 text-emerald-700 shadow-sm' 
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                  }
                `}
              >
                <div className="flex items-center gap-3">
                  <UserPlus className="w-5 h-5" />
                  Cadastros
                </div>
                <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${cadastroOpen ? 'rotate-180' : ''}`} />
              </button>
              
              {cadastroOpen && (
                <div className="ml-4 mt-2 space-y-1 animate-fade-in">
                  {cadastroItems.map((item) => (
                    <Link
                      key={item.path}
                      to={item.path}
                      onClick={() => setIsOpen(false)}
                      className={`
                        flex items-center gap-3 px-4 py-2 rounded-lg text-sm transition-all duration-200
                        ${isActive(item.path) 
                          ? 'bg-emerald-100 text-emerald-700' 
                          : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700'
                        }
                      `}
                    >
                      <item.icon className="w-4 h-4" />
                      {item.label}
                    </Link>
                  ))}
                </div>
              )}
            </div>

            {/* Additional Menu Items */}
            <Link
              to="/backup"
              onClick={() => setIsOpen(false)}
              className={`
                flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200
                ${isActive('/backup') 
                  ? 'bg-emerald-50 text-emerald-700 shadow-sm' 
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }
              `}
            >
              <Archive className="w-5 h-5" />
              Backup
            </Link>

            <Link
              to="/configuracoes"
              onClick={() => setIsOpen(false)}
              className={`
                flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200
                ${isActive('/configuracoes') 
                  ? 'bg-emerald-50 text-emerald-700 shadow-sm' 
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }
              `}
            >
              <Settings className="w-5 h-5" />
              Configurações
            </Link>
          </div>
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200">
          <Button
            onClick={handleLogout}
            variant="outline"
            className="w-full justify-start gap-3 text-slate-600 hover:text-red-600 hover:border-red-200 hover:bg-red-50"
          >
            <LogOut className="w-4 h-4" />
            Sair
          </Button>
        </div>
      </div>
    </>
  );
};

export default Sidebar;