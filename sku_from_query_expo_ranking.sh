#!/bin/bash

setcof="
SET hive.merge.mapfiles = true;
SET hive.merge.mapredfiles = true;
SET hive.merge.size.per.task = 2147483648;
SET hive.merge.smallfiles.avgsize = 2147483648;
SET hive.input.format = org.apache.hadoop.hive.ql.io.CombineHiveInputFormat;
SET hive.hadoop.supports.splittable.combineinputformat = true;
SET mapreduce.input.fileinputformat.split.maxsize = 2147483648;
SET mapreduce.input.fileinputformat.split.minsize =2147483648;
SET mapreduce.input.fileinputformat.split.minsize.per.node = 2147483648;
SET mapreduce.input.fileinputformat.split.minsize.per.rack = 2147483648;
"

DT=$1
i=1
let j=i+1
dt=`date -d "${DT} -${i} day" +%Y-%m-%d`
dt1=`date -d "${j} days ago" +%Y-%m-%d`
echo $dt
echo $dt1


CRE_SQL="
drop table if exists app.sku_from_query_expo_ranking_update;
CREATE TABLE IF NOT EXISTS app.sku_from_query_expo_ranking_update(
query string COMMENT 'key_word',
sku string COMMENT 'sku_id',
shop_id string COMMENT 'shop_id',
major_supp_brevity_code string COMMENT '主供应商简码',
item_name string COMMENT '商品名称',
square_pic_path string COMMENT '图片链接',
brand_code string COMMENT '品牌id',
barndname_full string COMMENT '品牌全名称',
item_first_cate_name string COMMENT '商品一级分类名称',
item_second_cate_name string COMMENT '商品二级分类名称',
item_third_cate_name string COMMENT '商品三级分类名称',
query_sku_rank int COMMENT '词下sku排名',
rank_change int COMMENT '排名变化',
before_rank int COMMENT '上次排名'
)
PARTITIONED BY (dt string)
ROW FORMAT DELIMITED FIELDS TERMINATED BY '\t' LINES TERMINATED BY '\n'
NULL DEFINED AS ''
STORED AS ORC
LOCATION '/user/recsys/rank/app.db/sku_from_query_expo_ranking_update'
tblproperties ('orc.compress' = 'SNAPPY', 'comment' = 'app端sku在query下的曝光排名','creator' = 'liujingxian6@jd.com');"

HQL="
$setcof
insert overwrite table app.sku_from_query_expo_ranking_update partition 
	(
		dt='${dt}'
	)
SELECT
	a.query,
	a.sku,
	shop_id,
	major_supp_brevity_code,
	item_name,
	square_pic_path,
	brand_code,
	barndname_full,
	item_first_cate_name,
	item_second_cate_name,
	item_third_cate_name,
	a.query_sku_rank,
	c.query_sku_rank - a.query_sku_rank AS rank_change,
	c.query_sku_rank AS before_rank
FROM
	(
		SELECT
			query,
			sku,
			query_sku_rank
		FROM
			(
				SELECT
					query,
					sku,
					rank(sku_avg_index) over(partition BY query order by expo_cnt DESC, sku_avg_index ASC) AS query_sku_rank
				FROM
					(
						SELECT
							--pvid, -- 验证pv后可丢掉
							sku,
							LOWER(key_word) AS query,
							AVG(INDEX) AS sku_avg_index,
							COUNT( *) AS expo_cnt,
							SUM(COUNT( *)) over(partition BY LOWER(key_word)) AS query_expo
							--row_number() over(partition BY pvid, sku order by request_time) AS rn
						FROM
							app.app_sdl_yinliu_search_query_log
						WHERE
							dt = '${dt}'
							AND dim_type = 'app'
							AND source = 0
							AND cheat_tag['L1'] = 0
							AND cheat_tag['L2_pv_logid'] = 0
							AND key_word <> ''
							AND true_expo = 1
							AND sort_type != 'sort_dredisprice'
						GROUP BY
							LOWER(key_word),
							sku
					)
					a
				WHERE
					expo_cnt > 1
					AND query_expo > 1000
			)
			a
		WHERE
			query_sku_rank <= 500
	)
	a
LEFT JOIN
	(
		SELECT
			item_sku_id,
			shop_id,
			major_supp_brevity_code,
			item_name,
			brand_code,
			barndname_full,
			item_first_cate_name,
			item_second_cate_name,
			item_third_cate_name
		FROM
			gdm.gdm_m03_item_sku_act
		WHERE
			dt = '${dt}'
			AND sku_valid_flag = 1 --sku有效标志
		GROUP BY
			item_sku_id,
			shop_id,
			major_supp_brevity_code,
			item_name,
			brand_code,
			barndname_full,
			item_first_cate_name,
			item_second_cate_name,
			item_third_cate_name
	)
	b
ON
	a.sku = b.item_sku_id
LEFT JOIN
	(
		SELECT
			query,
			sku,
			query_sku_rank
		FROM
			app.sku_from_query_expo_ranking_update
		WHERE
			dt = '${dt1}'
	)
	c
ON
	a.query = c.query
	AND a.sku = c.sku
LEFT JOIN
	(
		SELECT
			item_sku_id,
			square_pic_path
		FROM
			gdm.gdm_m03_search_item_sku_da
		WHERE
			dt = '${dt}'
			AND sku_valid_flag = 1
	)
	d
ON
	a.sku = d.item_sku_id
order by a.query,a.query_sku_rank ASC
"

HQL_old="
$setcof
insert overwrite table app.sku_from_query_expo_ranking partition 
	(
		dt='${dt}'
	)
SELECT
	query,
	sku,
	expo_cnt,
	sku_avg_index,
	expo_cnt / query_expo AS query_expo_ratio,
	rank(sku_avg_index) over(partition BY a.query order by expo_cnt DESC, sku_avg_index ASC) AS query_rank
FROM
	(
		SELECT
			sku,
			LOWER(key_word) AS query,
			AVG(INDEX) AS sku_avg_index,
			COUNT(*) AS expo_cnt,
			SUM(COUNT(*)) over(partition BY LOWER(key_word)) AS query_expo
		FROM
			app.app_sdl_yinliu_search_query_log
		WHERE
			dt = '${dt}'
			AND dim_type = 'app'
			AND source = 0
			AND cheat_tag['L1'] = 0
			AND cheat_tag['L2_pv_logid'] = 0
			AND key_word <> ''
			AND true_expo = 1
			AND sort_type != 'sort_dredisprice'
		GROUP BY
			LOWER(key_word),
			sku
	)
	a
WHERE expo_cnt>1
"
#hive -e "$CRE_SQL"
hive -e "$HQL"
hive -e "$HQL_old"

