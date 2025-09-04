import React, { useState, useEffect } from 'react';
import { useAuth } from '../App';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { 
  Clock, 
  AlertTriangle,
  Calendar,
  CreditCard,
  X,
  Mail,
  RefreshCw
} from 'lucide-react';
import { toast } from 'sonner';

const NotificacaoVencimento = ({ tenantId }) => {
  const { api, user } = useAuth();
  const [vencimentos, setVencimentos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);

  useEffect(() => {
    // Verifica vencimentos na inicialização
    if (user?.role === 'admin_empresa' && tenantId) {
      checkVencimentos();
    }
  }, [user, tenantId]);

  const checkVencimentos = async () => {
    setLoading(true);
    try {
      // Simula verificação de vencimentos - aqui você conectaria com sua API real
      const today = new Date();
      const in30Days = new Date(today.getTime() + 30 * 24 * 60 * 60 * 1000);
      
      // Exemplo de vencimentos próximos
      const mockVencimentos = [
        {
          id: 1,
          tipo: 'Plano Premium',
          dataVencimento: new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000),
          valor: 89.90,
          status: 'vencendo'
        },
        {
          id: 2,
          tipo: 'Certificado Digital',
          dataVencimento: new Date(today.getTime() + 15 * 24 * 60 * 60 * 1000),
          valor: 150.00,
          status: 'proximo'
        }
      ];

      setVencimentos(mockVencimentos);
      
      // Se há vencimentos próximos, mostra notificação
      if (mockVencimentos.length > 0) {
        setShowNotifications(true);
        toast.warning(`Você tem ${mockVencimentos.length} vencimento(s) próximo(s)!`);
      }
    } catch (error) {
      console.error('Erro ao verificar vencimentos:', error);
    } finally {
      setLoading(false);
    }
  };

  const sendEmailNotification = async (vencimento) => {
    try {
      setLoading(true);
      // Aqui você enviaria email via sua API
      toast.success('Notificação por email enviada com sucesso!');
    } catch (error) {
      toast.error('Erro ao enviar notificação por email');
    } finally {
      setLoading(false);
    }
  };

  const markAsNotified = (vencimentoId) => {
    setVencimentos(prev => prev.filter(v => v.id !== vencimentoId));
    if (vencimentos.length === 1) {
      setShowNotifications(false);
    }
  };

  const getDaysUntilExpiry = (date) => {
    const today = new Date();
    const diffTime = date - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'vencendo': return 'bg-red-50 text-red-700 border-red-200';
      case 'proximo': return 'bg-yellow-50 text-yellow-700 border-yellow-200';
      default: return 'bg-slate-50 text-slate-700 border-slate-200';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'vencendo': return 'Vencendo';
      case 'proximo': return 'Próximo';
      default: return status;
    }
  };

  if (!showNotifications || vencimentos.length === 0) {
    return null;
  }

  return (
    <div className="fixed top-4 right-4 z-50 w-80 animate-slide-in-right">
      <Card className="shadow-lg border-l-4 border-l-orange-500">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-orange-100 rounded-full flex items-center justify-center">
                <Clock className="w-4 h-4 text-orange-600" />
              </div>
              <CardTitle className="text-lg">Vencimentos Próximos</CardTitle>
            </div>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setShowNotifications(false)}
              className="h-8 w-8 p-0"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
        </CardHeader>
        
        <CardContent className="space-y-3">
          {vencimentos.map((vencimento) => {
            const daysLeft = getDaysUntilExpiry(vencimento.dataVencimento);
            
            return (
              <div key={vencimento.id} className="p-3 border border-slate-200 rounded-lg space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="font-medium text-slate-800">{vencimento.tipo}</h4>
                  <Badge className={`border ${getStatusColor(vencimento.status)}`}>
                    {getStatusText(vencimento.status)}
                  </Badge>
                </div>
                
                <div className="flex items-center gap-4 text-sm text-slate-600">
                  <div className="flex items-center gap-1">
                    <Calendar className="w-4 h-4" />
                    <span>{vencimento.dataVencimento.toLocaleDateString('pt-BR')}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <CreditCard className="w-4 h-4" />
                    <span>R$ {vencimento.valor.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</span>
                  </div>
                </div>
                
                <div className="flex items-center gap-2 text-sm">
                  {daysLeft <= 7 ? (
                    <div className="flex items-center gap-1 text-red-600">
                      <AlertTriangle className="w-4 h-4" />
                      <span className="font-medium">
                        {daysLeft === 0 ? 'Vence hoje!' : 
                         daysLeft === 1 ? 'Vence amanhã!' : 
                         `Vence em ${daysLeft} dias`}
                      </span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1 text-yellow-600">
                      <Clock className="w-4 h-4" />
                      <span>Vence em {daysLeft} dias</span>
                    </div>
                  )}
                </div>
                
                <div className="flex gap-2 pt-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => sendEmailNotification(vencimento)}
                    disabled={loading}
                    className="flex-1"
                  >
                    <Mail className="w-3 h-3 mr-1" />
                    Notificar por Email
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => markAsNotified(vencimento.id)}
                    className="px-3"
                  >
                    <X className="w-3 h-3" />
                  </Button>
                </div>
              </div>
            );
          })}
          
          <div className="pt-2 border-t border-slate-200">
            <Button
              size="sm"
              variant="ghost"
              onClick={checkVencimentos}
              disabled={loading}
              className="w-full"
            >
              {loading ? (
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4 mr-2" />
              )}
              Verificar Novamente
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default NotificacaoVencimento;