#!/usr/bin/env python
# -*- coding: utf-8 -*-
import datetime
import ast
import configparser

configfile="//Users//liujingxian6//Documents//ItemType//JiankongYujing//model_conf.ini"
if __name__ == "__main_":
    #class_data_CycleCheck执行
    CycleCheck = data_CycleCheck(data,cycle_day=365)
    df_power = CycleCheck.model_bosting()
    if df_power.loc[0,'rule_NoCycle'] ==1:
        print(df_power.loc[0,'ds'],'数据无周期性!')
    elif df_power.loc[0,'rule_AnomalyCycle'] == 1 and df_power.loc[0,'sen_anomaly'] == 1:
            print(df_power.loc[0,'ds'],'数据趋势异常！')
    else:
        start = datetime.datetime.now()
        #class_prophet_model执行
        data
        holidays_list = []
        lower_win = []
        upper_win = []
        freq = 'D'
        predict_freq_num = 1
        AnomalyTime = []
        prophet_model = model_prophet(data,holidays_list,lower_win,upper_win,freq,predict_freq_num,AnomalyTime)

        conf = configparser.ConfigParser()
        if not os.access(configfile,os.F_OK):
            conf['model_tag'] = {}
            conf['model_tag']['prophetModel_tag'] = getattr(prophet_model,'model_tag')
            with open(configfile, 'w') as configfile1:
                conf.write(configfile1)
        conf.read(configfile)
        model_tag = conf.get('model_tag','prophetModel_tag')
        if model_tag != 'offline':
            params = dict(conf.items('model_params'))
            for i in range(len(conf.items('model_params'))):
                a = str(conf.options("model_params")[i])
                if a in ['yearly_seasonality','weekly_seasonality','daily_seasonality',\
                         'changepoint_prior_scale','holidays_prior_scale','seasonality_prior_scale']:
                    params[a] = ast.literal_eval(params[a])
            prophet_model.load_model()
            forecast = prophet_model.predict_model()[['ds','yhat']]
            #prophet_model.update_model(params)
            #prophet_model.save_model()
        else:
            prophet_model.grid_search()
            prophet_model.save_model()
            conf['model_params'] = getattr(prophet_model,'params')

        conf['model_tag'] = {}
        conf['model_tag']['prophetModel_tag'] = getattr(prophet_model,'model_tag')
        with open(configfile, 'w') as configfile1:
            conf.write(configfile1)
        print(getattr(prophet_model,'model_tag'))

        end = datetime.datetime.now()
        print('运行时间:',(end-start))

        #class_DBScan_model执行
        OutRule = pd.merge(data,forecast,how ='inner',left_on='ds',right_on='ds')
        DBScan_model = model_DBScan(OutRule)
        DBScan_model.DBScan_run()