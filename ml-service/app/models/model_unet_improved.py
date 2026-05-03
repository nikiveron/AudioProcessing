import torch
import torch.nn as nn


class AttentionGate(nn.Module):
    """
    Attention Gate для skip connections.
    Помогает модели фокусироваться на важных областях.
    """
    def __init__(self, F_g, F_l, F_int):
        super().__init__()
        self.W_g = nn.Sequential(
            nn.Conv2d(F_g, F_int, kernel_size=1, stride=1, padding=0, bias=True),
            nn.BatchNorm2d(F_int)
        )
        self.W_x = nn.Sequential(
            nn.Conv2d(F_l, F_int, kernel_size=1, stride=1, padding=0, bias=True),
            nn.BatchNorm2d(F_int)
        )
        self.psi = nn.Sequential(
            nn.Conv2d(F_int, 1, kernel_size=1, stride=1, padding=0, bias=True),
            nn.BatchNorm2d(1),
            nn.Sigmoid()
        )
        self.relu = nn.ReLU(inplace=True)
        
    def forward(self, g, x):
        g1 = self.W_g(g)
        x1 = self.W_x(x)
        
        # Кропаем до одинаковых размеров если нужно
        _, _, g_freq, g_time = g1.shape
        _, _, x_freq, x_time = x1.shape
        
        min_freq = min(g_freq, x_freq)
        min_time = min(g_time, x_time)
        
        g1 = g1[:, :, :min_freq, :min_time]
        x1 = x1[:, :, :min_freq, :min_time]
        
        psi = self.psi(self.relu(g1 + x1))
        
        # Кропаем x до размера psi если нужно
        _, _, psi_freq, psi_time = psi.shape
        _, _, x_freq, x_time = x.shape
        
        if psi_freq != x_freq or psi_time != x_time:
            x = x[:, :, :psi_freq, :psi_time]
        
        return x * psi


class ResidualBlock(nn.Module):
    """
    Residual Block с двумя сверточными слоями.
    """
    def __init__(self, channels, dropout_rate=0.1):
        super().__init__()
        self.conv1 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(channels, channels, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(channels)
        self.dropout = nn.Dropout2d(dropout_rate)
        self.activation = nn.LeakyReLU(0.2, inplace=True)
        
    def forward(self, x):
        residual = x
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.activation(out)
        out = self.dropout(out)
        out = self.conv2(out)
        out = self.bn2(out)
        out = self.activation(out)
        out = out + residual
        return out


class ImprovedUNetSeparator(nn.Module):
    """
    Улучшенная U-Net архитектура с:
    - Attention Gates для skip connections
    - Residual Blocks в bottleneck
    - Улучшенной нормализацией
    
    Архитектура (оптимизирована для MPS):
    - Вход: 1 канал (magnitude спектрограмма)
    - Encoder: 3 уровня (меньше памяти)
    - Bottleneck: 2 Residual Blocks
    - Decoder: 3 уровня с Attention Gates
    - Выход: 1 канал
    
    Поток каналов (base_channels=32):
    Вход: 1 → 32
    Encoder:
    - e1: 32 → 64
    - e2: 64 → 128
    - e3: 128 → 256
    Bottleneck: 256 → 256
    Decoder:
    - decoder3: 256 → 128, cat с e2(128) = 256
    - decoder2: 256 → 64, cat с e1(64) = 128
    - decoder1: 128 → 32
    Выход: 32 → 1
    """
    
    def __init__(self, input_size=1025, base_channels=32, dropout_rate=0.1):
        super().__init__()
        
        self.input_size = input_size
        self.base_channels = base_channels
        
        # LeakyReLU вместо Mish для MPS совместимости
        self.activation = nn.LeakyReLU(0.2, inplace=True)
        
        # Входной слой: 1 → base_channels
        self.input_conv = nn.Sequential(
            nn.Conv2d(1, base_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(base_channels),
            self.activation
        )
        
        # Encoder: 3 уровня
        self.encoder1 = self._encoder_block(base_channels, base_channels * 2)   # 32 → 64
        self.encoder2 = self._encoder_block(base_channels * 2, base_channels * 4)  # 64 → 128
        self.encoder3 = self._encoder_block(base_channels * 4, base_channels * 8)  # 128 → 256
        
        # Bottleneck: 2 Residual Blocks
        self.bottleneck = nn.Sequential(
            ResidualBlock(base_channels * 8, dropout_rate),
            ResidualBlock(base_channels * 8, dropout_rate)
        )
        
        # Decoder с Attention Gates
        # decoder3: 256 → 128, cat с e2(128) = 256
        self.attention3 = AttentionGate(F_g=base_channels * 4, F_l=base_channels * 4, F_int=base_channels * 2)
        self.decoder3 = self._decoder_block(base_channels * 8, base_channels * 4)
        
        # decoder2: 256 → 64, cat с e1(64) = 128
        self.attention2 = AttentionGate(F_g=base_channels * 2, F_l=base_channels * 2, F_int=base_channels)
        self.decoder2 = self._decoder_block(base_channels * 8, base_channels * 2)
        
        # decoder1: 128 → 32
        self.attention1 = AttentionGate(F_g=base_channels, F_l=base_channels, F_int=base_channels // 2)
        self.decoder1 = self._decoder_block(base_channels * 4, base_channels)
        
        # Выходной слой: base_channels → 1
        self.output_conv = nn.Sequential(
            nn.Conv2d(base_channels, 1, kernel_size=3, padding=1),
            nn.Sigmoid()
        )
        
        self._init_weights()
    
    def _encoder_block(self, in_channels, out_channels):
        return nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(out_channels),
            self.activation,
            nn.Dropout2d(0.1)
        )
    
    def _decoder_block(self, in_channels, out_channels, dropout_rate=0.2):
        return nn.Sequential(
            nn.ConvTranspose2d(in_channels, out_channels, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(out_channels),
            self.activation,
            nn.Dropout2d(dropout_rate)
        )
    
    def _init_weights(self):
        """Инициализация весов"""
        for m in self.modules():
            if isinstance(m, (nn.Conv2d, nn.ConvTranspose2d)):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='leaky_relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
    
    def forward(self, x):
        """
        Forward pass.
        
        Args:
            x: Input tensor (batch, 1, freq, time) - magnitude спектрограмма
            
        Returns:
            output: Magnitude output (batch, 1, freq, time)
        """
        if x.dim() != 4:
            raise ValueError(f"Expected 4D input tensor (batch, 1, freq, time), got {x.dim()}D")
        
        # Сохраняем оригинальные размеры
        orig_freq = x.size(2)
        orig_time = x.size(3)
        
        # Входной слой
        x = self.input_conv(x)
        
        # Encoder с сохранением skip connections (3 уровня)
        e1 = self.encoder1(x)      # (batch, 64, freq/2, time/2)
        e2 = self.encoder2(e1)     # (batch, 128, freq/4, time/4)
        e3 = self.encoder3(e2)     # (batch, 256, freq/8, time/8)
        
        # Bottleneck
        x = self.bottleneck(e3)    # (batch, 256, freq/8, time/8)
        
        # Decoder с Attention Gates и skip connections
        # decoder3: 256 → 128
        x = self.decoder3(x)       # (batch, 128, freq/4, time/4)
        e2_attended = self.attention3(x, e2)  # (batch, 128, freq/4, time/4)
        x = torch.cat([x, e2_attended], dim=1)  # (batch, 256, freq/4, time/4)
        
        # decoder2: 256 → 64
        x = self.decoder2(x)       # (batch, 64, freq/2, time/2)
        e1_attended = self.attention2(x, e1)  # (batch, 64, freq/2, time/2)
        x = torch.cat([x, e1_attended], dim=1)  # (batch, 128, freq/2, time/2)
        
        # decoder1: 128 → 32
        x = self.decoder1(x)       # (batch, 32, freq, time)
        
        # Выходной слой
        output = self.output_conv(x)  # (batch, 1, freq, time)
        
        # Кроп до оригинального размера
        output = output[:, :, :orig_freq, :orig_time]
        
        return output
    
    def __repr__(self):
        return (
            f"ImprovedUNetSeparator(\n"
            f"  input_size={self.input_size},\n"
            f"  base_channels={self.base_channels},\n"
            f"  architecture: U-Net + Attention Gates + Residual Blocks\n"
            f")"
        )


class ImprovedComplexUNetSeparator(nn.Module):
    """
    Улучшенная Complex U-Net архитектура с attention gates.
    """
    
    def __init__(self, input_size=1025, base_channels=64, dropout_rate=0.2):
        super().__init__()
        
        self.input_size = input_size
        self.base_channels = base_channels
        self.activation = nn.Mish(inplace=True)
        
        # Вход: 2 канала (real, imag)
        self.input_conv = nn.Sequential(
            nn.Conv2d(2, base_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(base_channels),
            self.activation
        )
        
        # Encoder
        self.encoder1 = self._encoder_block(base_channels, base_channels * 2)
        self.encoder2 = self._encoder_block(base_channels * 2, base_channels * 4)
        self.encoder3 = self._encoder_block(base_channels * 4, base_channels * 8)
        self.encoder4 = self._encoder_block(base_channels * 8, base_channels * 16)
        
        # Bottleneck с Complex Conv
        self.bottleneck = nn.Sequential(
            ComplexConv2d(base_channels * 16, base_channels * 16, kernel_size=3, padding=1),
            nn.BatchNorm2d(base_channels * 16),
            self.activation,
            ComplexConv2d(base_channels * 16, base_channels * 16, kernel_size=3, padding=1),
            nn.BatchNorm2d(base_channels * 16),
            self.activation
        )
        
        # Attention Gates
        self.attention4 = AttentionGate(base_channels * 8, base_channels * 16, base_channels * 8)
        self.decoder4 = self._decoder_block(base_channels * 16 + base_channels * 8, base_channels * 8)
        
        self.attention3 = AttentionGate(base_channels * 4, base_channels * 8, base_channels * 4)
        self.decoder3 = self._decoder_block(base_channels * 8 + base_channels * 4, base_channels * 4)
        
        self.attention2 = AttentionGate(base_channels * 2, base_channels * 4, base_channels * 2)
        self.decoder2 = self._decoder_block(base_channels * 4 + base_channels * 2, base_channels * 2)
        
        self.attention1 = AttentionGate(base_channels, base_channels * 2, base_channels)
        self.decoder1 = self._decoder_block(base_channels * 2 + base_channels, base_channels)
        
        # Выход: 2 канала (real_out, imag_out)
        self.output_conv = nn.Sequential(
            nn.Conv2d(base_channels, 2, kernel_size=3, padding=1),
            nn.Tanh()
        )
        
        self._init_weights()
    
    def _encoder_block(self, in_channels, out_channels):
        return nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(out_channels),
            self.activation
        )
    
    def _decoder_block(self, in_channels, out_channels):
        return nn.Sequential(
            nn.ConvTranspose2d(in_channels, out_channels, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(out_channels),
            self.activation
        )
    
    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, (nn.Conv2d, nn.ConvTranspose2d)):
                # Mish не поддерживается в kaiming_normal_, используем leaky_relu как аппроксимацию
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='leaky_relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
    
    def forward(self, x):
        if x.dim() != 4:
            raise ValueError(f"Expected 4D input tensor (batch, 1, freq, time), got {x.dim()}D")
        
        # Создаём комплексный вход из magnitude
        real_in = x
        imag_in = torch.zeros_like(x)
        x_complex = torch.cat([real_in, imag_in], dim=1)
        
        x = self.input_conv(x_complex)
        
        # Encoder
        e1 = self.encoder1(x)
        e2 = self.encoder2(e1)
        e3 = self.encoder3(e2)
        e4 = self.encoder4(e3)
        
        # Bottleneck
        x = self.bottleneck(e4)
        
        # Decoder с Attention Gates
        x = self.decoder4(x)
        e3_attended = self.attention4(x, e3)
        x = torch.cat([x, e3_attended], dim=1)
        
        x = self.decoder3(x)
        e2_attended = self.attention3(x, e2)
        x = torch.cat([x, e2_attended], dim=1)
        
        x = self.decoder2(x)
        e1_attended = self.attention2(x, e1)
        x = torch.cat([x, e1_attended], dim=1)
        
        x = self.decoder1(x)
        
        # Выход + residual connection
        output = self.output_conv(x)
        output = output + x_complex
        
        return output
    
    def __repr__(self):
        return (
            f"ImprovedComplexUNetSeparator(\n"
            f"  input_size={self.input_size},\n"
            f"  base_channels={self.base_channels},\n"
            f"  architecture: Complex U-Net + Attention Gates\n"
            f")"
        )


class ComplexConv2d(nn.Module):
    """Complex-valued 2D convolution layer."""
    def __init__(self, in_channels, out_channels, kernel_size, stride=1, padding=0):
        super().__init__()
        self.conv_real = nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding)
        self.conv_imag = nn.Conv2d(in_channels, out_channels, kernel_size, stride, padding)
        
    def forward(self, x):
        batch, channels, freq, time = x.shape
        half_channels = channels // 2
        
        real_in = x[:, :half_channels, :, :]
        imag_in = x[:, half_channels:, :, :]
        
        real_out = self.conv_real(real_in) - self.conv_imag(imag_in)
        imag_out = self.conv_real(imag_in) + self.conv_imag(real_in)
        
        return torch.cat([real_out, imag_out], dim=1)
