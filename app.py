from flask import Flask
from flask_cors import CORS
from flask_pymongo import PyMongo
from bson.json_util import dumps
from bson.objectid import ObjectId
from flask import jsonify, request
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import MinMaxScaler
import numpy as np

app = Flask(__name__)
CORS(app)

app.config['MONGO_URI'] = "mongodb+srv://truong:vminkook@apartfinding.liwqnyu.mongodb.net/test"
# set up mongodb
mongo = PyMongo(app)
# db = mongodb_client.db

@app.route('/posts/<id>',  methods=['GET'])
def recommend(id):
  def hashType(id, types): 
    for i,x in enumerate(types):
      if id == x:
        return i
      
  def fillGender(gender):
    if gender == 'any':
      return 0
    elif gender == 'male':
      return 1
    else: return 2
      
  num = 6
  list = []

  types = []
  for t in mongo.db.renttypes.find():
    types.append(str(t["_id"]))

  post = mongo.db.posts.find_one({ '_id': ObjectId(id)})
  postEl = [str(post["_id"]), hashType(str(post["rentType"]), types), post["price"], post["area"], 
            post["fullAddressObject"]["district"]["code"], post["fullAddressObject"]["ward"]["code"], fillGender(post["gender"])]
  
  postsList = []
  posts = []
  results = mongo.db.posts.find({ 'fullAddressObject.ward.code': post["fullAddressObject"]["ward"]["code"], 
                                  'rentType': post["rentType"]})
  if results.explain().get("executionStats", {}).get("nReturned") < num:
    results = mongo.db.posts.find({ 'fullAddressObject.district.code': post["fullAddressObject"]["district"]["code"],
                                    'rentType': post["rentType"]})
    if results.explain().get("executionStats", {}).get("nReturned") < num:
      results = mongo.db.posts.find({ 'rentType': post["rentType"]})
  
  count = results.explain().get("executionStats", {}).get("nReturned")
  for p in results:
    posts.append(p)
    data = [str(p["_id"]), hashType(str(p["rentType"]), types), p["price"], p["area"], 
            p["fullAddressObject"]["district"]["code"], p["fullAddressObject"]["ward"]["code"], fillGender(p["gender"])]
    postsList.append(data)

  postIndex = 0
  for p in postsList:
    if p[0] == postEl[0]:
      postIndex = postsList.index(p)
    
  postsArray = np.array(postsList)
  postSlice = postsArray[:, 1:7]
  dataSet = postSlice.astype(float)
  # dataSet = postSlice.astype(int)
  scaler = MinMaxScaler()
  scaler.fit(dataSet)
  data = scaler.transform(dataSet)

  if count < num:
    nbrs = NearestNeighbors(n_neighbors=count).fit(data)
  else:
    nbrs = NearestNeighbors(n_neighbors=num).fit(data)
    
  distances, indices = nbrs.kneighbors([data[postIndex]])
  resultArr = indices.tolist()
  result = resultArr[0]
  result.remove(postIndex)

  for x in result:
    list.append(posts[x])

  resp = dumps(list)
  return resp
  
@app.errorhandler(404)
def not_found(error=None):
  message = {
    'status': 404,
    'message': 'Not found ' + request.url
  }
  resp = jsonify(message)
  resp.status_code = 404
  return resp

if __name__ == "__main__":
  app.run(debug=True, port=8001)