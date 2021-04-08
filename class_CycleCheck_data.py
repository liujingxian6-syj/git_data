#!/usr/bin/env python
# -*- coding: utf-8 -*-
from sklearn import linear_model
import numpy as np
from scipy.fftpack import fft
import matplotlib.pyplot as plt
class data_CycleCheck():
    def __init__(self,data,cycle_day,sen_level=90,N=5):
        self.data = data
        self.data['ds'] = pd.to_datetime(self.data['ds'])
        self.sen_level=sen_level
        self.N = N
        self.cycle_day = cycle_day
        
    def fft_model(self,data,before_power):
        N = self.N
        #取出y
        y = np.array(data['y'])
        data0 = np.array(y)
        
        #移动平均滤波器
        n=np.ones(N)
        weights=n/N
        t_code=np.arange(N-1,len(data0))
        sma=np.convolve(weights,data0)[N-1:-N+1]
        #plt.plot(t_code,data0[N-1:],label='原信号')  
        #plt.plot(t_code,sma,label='滤波') 
    
        #消除长期趋势
        reg = linear_model.LinearRegression()
        reg.fit (t_code.reshape(-1,1),sma.reshape(-1,1))
        b = reg.coef_[0][0]
        sma1=sma-(b*t_code)
        
        #FFT频谱分析
        L = len(sma1)                        # 信号长度
        FFT_y1 = np.power(np.abs(fft(sma1)),2)              # FFT变换，取傅里叶系数的平方
        Fre = (np.arange(1,int(L/2)+2)/L)
        period = 1/Fre
        FFT_y1 = FFT_y1[range(1,int(L/2)+2)]      # 取一半
        #plt.plot(period,FFT_y1) 

        #记录较大能量
        num1 = np.max(FFT_y1)
        num2 = np.max(FFT_y1[FFT_y1 <num1])
        num3 = np.max(FFT_y1[FFT_y1 <num2])
        num4 = np.max(FFT_y1[FFT_y1 <num3])
        num5 = np.max(FFT_y1[FFT_y1 <num4])
        num=[num1,num2,num3,num4,num5]
        #记录较大能量对应周期
        c1 = round(period[np.argmax(FFT_y1)])+1
        c2 = period[int(np.argwhere(FFT_y1==num2))]+1
        c3 = period[int(np.argwhere(FFT_y1==num3))]+1
        c4 = period[int(np.argwhere(FFT_y1==num4))]+1
        c5 = period[int(np.argwhere(FFT_y1==num5))]+1

        #最大频率所对应的周期& Top5频率所对应周期中的最大周期
        cycle_max = round(np.max([c1,c2,c3,c4,c5]))
        cycle_max_power = num[np.argmax([c1,c2,c3,c4,c5])]
        df_power = data.iloc[-1:].reset_index(drop=True)
        df_power.loc[:,'cycle'] = c1
        df_power.loc[:,'cycle_max'] = cycle_max
        df_power.loc[:,'cycle_max_power'] = cycle_max_power

        # 异常趋势标签：完全无周期性&有周期性但因趋势异常导致周期发生变化
        df_power.loc[:,'rule_NoCycle'] = 0
        df_power.loc[np.round(df_power['cycle']/len(data))==1,'rule_NoCycle'] = 1

        df_power.loc[:,'rule_AnomalyCycle'] = 0
        df_power.loc[:,'before_power'] = before_power
        df_power.loc[(df_power['rule_NoCycle']==0)&(df_power['cycle_max_power']>before_power)&(np.round(df_power['cycle_max']/len(data))==1),'rule_AnomalyCycle'] = 1

        before_power = cycle_max_power
        return df_power 

    def data_sens(self):
        data = self.data
        cycle_day = self.cycle_day 
        start_time = data['ds'].max() - datetime.timedelta(days=cycle_day)
        end_time = data['ds'].max()
        periods_cycle = len(data.loc[(data['ds']>start_time)&(data['ds']<=end_time)])

        df_diff = data.iloc[-1:].reset_index(drop=True)
        df_diff.loc[:,'diff_cycle'] = data['y'].diff(periods=periods_cycle).iloc[-1:].reset_index(drop=True)
        df_diff.loc[:,'sen_threshold'] = np.percentile(np.abs(data['y'].diff(periods=1).dropna()),self.sen_level)
        df_diff.loc[:,'sen_anomaly'] = 0
        df_diff.loc[np.abs(df_diff['diff_cycle'])>df_diff['sen_threshold'],'sen_anomaly'] = 1
        return df_diff
    
    def model_bosting(self):
        data =self.data
        before_power = 0
        df1 = data.loc[data['ds'] < data['ds'].max(),:]
        before_power = self.fft_model(df1,before_power)['cycle_max_power']
        df_power = pd.concat([self.fft_model(data,before_power),self.data_sens()[['diff_cycle','sen_threshold','sen_anomaly']]],axis=1)
        return df_power
        