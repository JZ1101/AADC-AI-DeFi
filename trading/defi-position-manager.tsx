import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ArrowUpDown, AlertTriangle, CheckCircle } from 'lucide-react';

// Mock GMX contract interface - In production, you'd use actual contract ABIs
const GMX_CONTRACTS = {
  AVALANCHE: {
    Vault: '0x9ab2De34A33fB459b538c43f251eB825645e8595',
    Router: '0x5F719c2F1095F7B9fc68a68e35B51194f4b6abe8',
  }
};

const PositionManager = () => {
  const [positions, setPositions] = useState([
    {
      id: 1,
      protocol: 'GMX',
      asset: 'AVAX-USD',
      size: '1000',
      leverage: '2.5',
      direction: 'LONG',
      entryPrice: '35.50',
      liquidationPrice: '28.40',
      pnl: '+125.5',
    }
  ]);

  const [selectedPosition, setSelectedPosition] = useState(null);
  const [actionType, setActionType] = useState('');
  const [amount, setAmount] = useState('');
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [previewData, setPreviewData] = useState(null);

  // Simulate fetching positions from GMX
  useEffect(() => {
    const fetchPositions = async () => {
      // In production: Actually fetch positions from GMX contracts
      console.log('Fetching positions from GMX on Avalanche...');
    };

    fetchPositions();
  }, []);

  const handlePositionAction = async (action) => {
    setActionType(action);
    setShowConfirmation(true);
    
    // Calculate preview data based on action
    const preview = calculatePreview(action, selectedPosition, amount);
    setPreviewData(preview);
  };

  const calculatePreview = (action, position, amount) => {
    if (!position) return null;
    
    // In production: Use actual GMX contract calls for previews
    switch (action) {
      case 'INCREASE':
        return {
          estimatedFee: '0.05 AVAX',
          newLeverage: (parseFloat(position.leverage) * 1.5).toFixed(2),
          liquidationPrice: (parseFloat(position.liquidationPrice) * 0.9).toFixed(2),
        };
      case 'DECREASE':
        return {
          estimatedFee: '0.04 AVAX',
          newLeverage: (parseFloat(position.leverage) * 0.75).toFixed(2),
          liquidationPrice: (parseFloat(position.liquidationPrice) * 1.1).toFixed(2),
        };
      default:
        return null;
    }
  };

  const confirmAction = async () => {
    // In production: Execute actual GMX contract calls
    console.log(`Executing ${actionType} on GMX position ${selectedPosition?.id}`);
    
    // Simulate position update
    const updatedPositions = positions.map(pos => {
      if (pos.id === selectedPosition?.id) {
        return {
          ...pos,
          size: actionType === 'INCREASE' 
            ? (parseFloat(pos.size) + parseFloat(amount)).toString()
            : (parseFloat(pos.size) - parseFloat(amount)).toString(),
          leverage: previewData.newLeverage,
          liquidationPrice: previewData.liquidationPrice,
        };
      }
      return pos;
    });
    
    setPositions(updatedPositions);
    setShowConfirmation(false);
    setSelectedPosition(null);
    setAmount('');
  };

  return (
    <Card className="w-full max-w-4xl">
      <CardHeader>
        <CardTitle>GMX Position Manager on Avalanche</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Positions List */}
          <div className="space-y-4">
            {positions.map((position) => (
              <div
                key={position.id}
                className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                  selectedPosition?.id === position.id
                    ? 'border-blue-500 bg-blue-50'
                    : 'hover:border-gray-300'
                }`}
                onClick={() => setSelectedPosition(position)}
              >
                <div className="flex justify-between items-center">
                  <div>
                    <h3 className="font-semibold">{position.asset}</h3>
                    <p className="text-sm text-gray-600">
                      Size: {position.size} USD • Leverage: {position.leverage}x
                    </p>
                  </div>
                  <div className="text-right">
                    <p className={`font-bold ${
                      position.pnl.startsWith('+') ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {position.pnl} USD
                    </p>
                    <p className="text-sm text-gray-600">
                      Entry: ${position.entryPrice}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Position Actions */}
          {selectedPosition && (
            <div className="space-y-4 p-4 border rounded-lg">
              <h3 className="font-semibold">Position Actions</h3>
              <div className="flex gap-4">
                <Input
                  type="number"
                  placeholder="Amount (USD)"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  className="max-w-xs"
                />
                <Button
                  onClick={() => handlePositionAction('INCREASE')}
                  disabled={!amount}
                  className="bg-green-600 hover:bg-green-700"
                >
                  Increase Position
                </Button>
                <Button
                  onClick={() => handlePositionAction('DECREASE')}
                  disabled={!amount}
                  className="bg-red-600 hover:bg-red-700"
                >
                  Decrease Position
                </Button>
              </div>
            </div>
          )}

          {/* Confirmation Modal */}
          {showConfirmation && previewData && (
            <Alert className="mt-4">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <div className="space-y-2">
                  <h4 className="font-semibold">Confirm {actionType} Position</h4>
                  <p>Amount: {amount} USD</p>
                  <p>Estimated Fee: {previewData.estimatedFee}</p>
                  <p>New Leverage: {previewData.newLeverage}x</p>
                  <p>New Liquidation Price: ${previewData.liquidationPrice}</p>
                  <div className="flex gap-4 mt-4">
                    <Button onClick={confirmAction} className="bg-blue-600">
                      Confirm
                    </Button>
                    <Button 
                      onClick={() => setShowConfirmation(false)}
                      variant="outline"
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              </AlertDescription>
            </Alert>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default PositionManager;