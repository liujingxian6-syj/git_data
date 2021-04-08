#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import joblib
from fbprophet import Prophet
from fbprophet.diagnostics import cross_validation
from fbprophet.diagnostics import performance_metrics 
from fbprophet.plot import plot_cross_validation_metric
from itertools import product
import datetime

class model_prophet():
    parameters_grid = {
        'yearly_seasonality': [True,False],
        'weekly_seasonality': [True,False],
        'daily_seasonality': [True,False], 
        'seasonality_mode': ['additive','multiplicative']
        }
    
    parameters_add = {
        "changepoint_prior_scale": list(np.arange(0.05, 10, 0.5)), 
        "holidays_prior_scale": list(np.arange(10, 0, -1)),
        "seasonality_prior_scale": list(np.arange(10, 0, -1))
        }

    def __init__(self,data,holidays_list,lower_win,upper_win,freq,predict_freq_num,anomaly_time):  
        self.holidays_list = holidays_list
        self.lower_win = lower_win
        self.upper_win = upper_win
        self.holidays = pd.DataFrame({
                          'holiday': 'holidays1',
                          'ds': pd.to_datetime(self.holidays_list),
                          'lower_window': self.lower_win,
                          'upper_window': self.upper_win
                        })

        self.predict_freq_num = predict_freq_num
        self.freq = freq
        
        self.data = data
        self.data['ds'] = pd.to_datetime(self.data['ds'])  #dt字符串转日期格式
        self.anomaly_time = anomaly_time
        self.params = {}
        self.mape = np.inf
        self.history_model = None
        self.model_tag = 'offline'
        self.model_save_path = '//Users//liujingxian6//Documents//ItemType//JiankongYujing//code//'  
        self.last_mape = 10000000000
    
    def __clean_data(self):
        if len(self.anomaly_time)>0:
            AnomalyTime=pd.to_datetime(pd.DataFrame(self.anomaly_time)[0]).tolist()
            self.data.loc[self.data['ds'].isin(AnomalyTime),'y']=np.nan  #异常时间点用空值替换
        return self.data
    
    def __cv_run(self,params):
        #交叉验证过程
        model = Prophet(**params,holidays=self.holidays)  
        model.fit(self.data)
        future = model.make_future_dataframe(freq=self.freq,periods=1) 
        forecast = model.predict(future)
        data_merage = pd.concat([self.data,forecast[['yhat']]],axis=1, join='inner')
        mape_train = np.abs(data_merage['yhat']/data_merage['y']-1).mean()
        
        
        initial_value = (self.data['ds'].max()-self.data['ds'].min()).days/1.9
        if 1.5< initial_value < 5 or 7< initial_value < 194 or initial_value > 368:
            initial_value = (self.data['ds'].max()-self.data['ds'].min())/1.9
            horizon_weight = 1-1/1.9
            df_cv = cross_validation(model, initial=(self.data['ds'].max()-sef.data['ds'].min())/1.9, \
                                     period=(self.data['ds'].max()-self.data['ds'].min())/4.2, \
                                     horizon =(self.data['ds'].max()-self.data['ds'].min())/2.2)
        elif initial_value <= 1.5:
            initial_value = '25 hours'
            period_value = '25 hours'
            horizon_value = self.data['ds'].max()-self.data['ds'].min()-datetime.timedelta(hours=25)
            horizon_weight = horizon_value/(self.data['ds'].max()-self.data['ds'].min())
            df_cv = cross_validation(model, initial=initial_value, period=period_value,horizon=horizon_value)
        elif initial_value <= 7:
            initial_value = '8 days'
            period_value = '8 days'
            horizon_value = self.data['ds'].max()-self.data['ds'].min()-datetime.timedelta(days=8)
            horizon_weight = horizon_value/(self.data['ds'].max()-self.data['ds'].min())
            df_cv = cross_validation(model, initial=initial_value, period=period_value,horizon=horizon_value)
        else:
            initial_value = '367 days'
            period_value = '367 days'
            horizon_value = self.data['ds'].max()-self.data['ds'].min()-datetime.timedelta(days=367)
            horizon_weight = horizon_value/(self.data['ds'].max()-self.data['ds'].min())
            df_cv = cross_validation(model, initial=initial_value, period=period_value,horizon=horizon_value)
        mape = horizon_weight*performance_metrics(df_cv, metrics=['mape'])['mape'].mean() +(1-horizon_weight)*mape_train     
        return mape
    
    def grid_search(self):
        """
        首先，对枚举参数结合cv进行网格寻参
        """
        parameters_grid = prophet_model.parameters_grid
        parameters_add = prophet_model.parameters_add
        self.__clean_data() 
        
        if len(parameters_grid)>0:
            ll = []
            for _,value in enumerate(parameters_grid):
                ll.append(parameters_grid[value])
            length_parms = len(parameters_grid)
            keys = list(parameters_grid.keys())
            for i in product(*ll):  
                params = {}
                for j in range(length_parms):
                    params.setdefault(keys[j],i[j])
                mape = self.__cv_run(params)
                if self.mape > mape:
                    self.mape = mape
                    self.params = params 
            #print(self.params,self.mape)  #仅测试用
        
        """
        然后，利用网格搜索的结果，对区间参数再单个参数使用坐标下降的方法结合Cv找最优
        """
        if len(parameters_add)>0:
            a=[]
            for i in list(self.params.values()):
                a.append([i])
            parameters = dict(dict(zip(list(self.params.keys()),a)), **parameters_add)

            names = parameters.keys()
            setups = [list(param) for param in parameters.values()]
            i = len(setups) - 1
            j = 0
            current_setup = [s[0] for s in setups]
            while self.mape > 0.001:
                if i >= 0 and j >= len(setups[i]):                      # all values of this param have been tried
                    j = 1
                    i -= 1
                    if len(setups[i])==1:
                        continue
                if i < 0:                                                               # no param could adjust
                    break
                current_setup[i] = setups[i][j]
                params = dict(zip(names, current_setup))
                #print(params, i, j)  

                mape = self.__cv_run(params)
                print(f"mape: {mape}")
                if mape < self.mape:
                    self.mape = mape
                    self.params = params
                if mape > self.last_mape*1.2:                     # cp_cut, consider all parameter is linear correlated with mape
                    i -= 1
                    j = 1
                    continue
                self.last_mape = mape
                j += 1
            #print(self.mape, self.params)  #仅测试用
            
        self.history_model = Prophet(**self.params,holidays=self.holidays)
        self.history_model.fit(self.data)
        self.model_tag = 'started'
        
        #以下仅测试用
        '''
        future = self.history_model.make_future_dataframe(freq=self.freq,periods=self.predict_freq_num)  
        forecast = self.history_model.predict(future)
        self.history_model.plot(forecast).show()
        self.history_model.plot_components(forecast).show()
        print(f'score:{self.mape}\nparams:{self.params}')
        '''
        return self.params,self.mape,self.history_model,self.model_tag     

    def save_model(self):
        if self.model_tag == 'started' or self.model_tag == 'online':
            joblib.dump(self.history_model, self.model_save_path+"prophet_model.m")
            return self.history_model
        else:
            print('未找到可存储模型！')

    def load_model(self):
        if os.access(self.model_save_path+"prophet_model.m",os.F_OK):
            self.history_model = joblib.load(self.model_save_path+"prophet_model.m")
            self.model_tag = 'load'
            return self.history_model 
        else:
            print('未找到可加载模型！')       
    
    #@staticmethod
    def __stan_init(self):
        m = self.history_model
        res = {}
        for pname in ['k', 'm', 'sigma_obs']:
            res[pname] = m.params[pname][0][0]
        for pname in ['delta', 'beta']:
            res[pname] = m.params[pname][0]
        return res

    def update_model(self,params):
        if self.model_tag == 'load':
            self.__clean_data()

            model = Prophet(**params,holidays=self.holidays)
            model.fit(self.data, init=self.__stan_init())
            self.history_model = model
            self.model_tag = 'online'
            return self.history_model
        else:
            print('未找到可更新模型！')
        
    def predict_model(self):
        if self.model_tag == 'load':
            model = self.history_model 
            future = model.make_future_dataframe(freq=self.freq,periods=self.predict_freq_num)  
            forecast = model.predict(future)
            predict_gap = self.data['ds'].max() - forecast['ds'].max()              
            data_freq = self.data['ds'].max() - self.data.loc[self.data['ds']<self.data['ds'].max(),'ds'].max()
            freq_gap = predict_gap/data_freq
            if freq_gap == 0:
                model.plot(forecast).show()
                return forecast
            elif freq_gap > 0:
                future = model.make_future_dataframe(freq=self.freq,periods=int(self.predict_freq_num*(freq_gap+1)))  
                forecast = model.predict(future)
                model.plot(forecast).show()
                return forecast
            else:
                print('请更新最新数据!')
        else:
            print('未找到可预测模型！')