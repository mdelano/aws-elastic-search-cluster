#!/bin/bash

readonly SCRIPT_NAME=$(basename $0)

log() {
  echo "$@"
  logger -p user.notice -t $SCRIPT_NAME "$@"
}

# fab create_host:ami-427a392a,c3.xlarge,us-east-1,us-east-1a,dev,elasticsearch X 5
source_host="ec2-54-204-65-194.compute-1.amazonaws.com"
source_index_name="phoenix"
backup_index_name="phoenix_backup"
target_host="localhost"
snapshot_name="snapshot_"`date +%s`
snapshot_repository="s3_backup_repository"





# Create snapshot repository on target
snapshot_repository_create_cmd="curl -XPUT \"http://$target_host:9200/_snapshot/$snapshot_repository\" -d '{\"type\": \"s3\",\"settings\": {\"bucket\": \"elasticsearch.backups.mediasilo.com\",\"region\": \"us-east-1\"}}'"
log "Creating Snapshot Repository:"
log "==================>Executing: $snapshot_repository_create_cmd"
eval $snapshot_repository_create_cmd




# Snapshot source DB
snaphshot_cmd="curl -XPUT \"http://$source_host:9200/_snapshot/$snapshot_repository/$snapshot_name?wait_for_completion=true\" --max-time 2000 -d '{\"indices\": \"phoenix,events,analytics\"}'"
log "Snapshotting source DB:"
log "==================>Executing: $snaphshot_cmd"
eval $snaphshot_cmd




# Restore DB
restore_cmd="curl -XPOST \"http://$target_host:9200/_snapshot/$snapshot_repository/$snapshot_name/_restore?wait_for_completion=true\" --max-time 2000 -d '{\"indices\": \"phoenix,events,analytics\"}'"
log "Restoring DB to target host:"
log "==================>Executing: $restore_cmd"
eval $restore_cmd





# Create backup index
curl -X POST "http://$target_host:9200/$backup_index_name" -d \
'{
      "aliases": {},
      "mappings": {
         "metadata": {
            "_parent": {
               "type": "asset"
            },
            "_routing": {
               "required": true
            },
            "properties": {
               "createdBy": {
                  "type": "string",
                  "index": "not_analyzed"
               },
               "id": {
                  "type": "long"
               },
               "key": {
                  "type": "string",
                  "index": "not_analyzed"
               },
               "type": {
                  "type": "string",
                  "index": "not_analyzed"
               },
               "value": {
                  "type": "string",
                  "index": "not_analyzed"
               },
               "valueType": {
                  "type": "string",
                  "index": "not_analyzed"
               }
            }
         },
         "transcript": {
            "_parent": {
               "type": "asset"
            },
            "_routing": {
               "required": true
            },
            "properties": {
               "formats": {
                  "properties": {
                     "ParagraphJSON": {
                        "type": "string"
                     },
                     "TimecodedJSON": {
                        "type": "string"
                     }
                  }
               },
               "logs": {
                  "properties": {
                     "description": {
                        "type": "string"
                     },
                     "endMilliseconds": {
                        "type": "long"
                     },
                     "speaker": {
                        "type": "string",
                        "index": "not_analyzed"
                     },
                     "startMilliseconds": {
                        "type": "long"
                     }
                  }
               }
            }
         },
         "rating": {
            "_parent": {
               "type": "asset"
            },
            "_routing": {
               "required": true
            },
            "properties": {
               "dateCreated": {
                  "type": "long"
               },
               "id": {
                  "type": "long"
               },
               "owner": {
                  "properties": {
                     "email": {
                        "type": "string"
                     },
                     "firstName": {
                        "type": "string"
                     },
                     "id": {
                        "type": "string"
                     },
                     "lastName": {
                        "type": "string"
                     },
                     "tags": {
                        "type": "string"
                     },
                     "userName": {
                        "type": "string"
                     }
                  }
               },
               "ownerId": {
                  "type": "string",
                  "index": "not_analyzed"
               },
               "rating": {
                  "type": "double"
               }
            }
         },
         "comment": {
            "_parent": {
               "type": "asset"
            },
            "_routing": {
               "required": true
            },
            "properties": {
               "at": {
                  "type": "string",
                  "index": "not_analyzed"
               },
               "body": {
                  "type": "string",
                  "fields": {
                     "raw": {
                        "type": "string",
                        "index": "not_analyzed"
                     }
                  }
               },
               "context": {
                  "type": "string",
                  "index": "not_analyzed"
               },
               "dateCreated": {
                  "type": "long"
               },
               "endTimeCode": {
                  "type": "long"
               },
               "id": {
                  "type": "string",
                  "index": "not_analyzed"
               },
               "inResponseTo": {
                  "type": "string",
                  "index": "not_analyzed"
               },
               "responses": {
                  "properties": {
                     "at": {
                        "type": "string",
                        "index": "not_analyzed"
                     },
                     "body": {
                        "type": "string",
                        "fields": {
                           "raw": {
                              "type": "string",
                              "index": "not_analyzed"
                           }
                        }
                     },
                     "context": {
                        "type": "string",
                        "index": "not_analyzed"
                     },
                     "dateCreated": {
                        "type": "long"
                     },
                     "endTimeCode": {
                        "type": "long"
                     },
                     "id": {
                        "type": "string",
                        "index": "not_analyzed"
                     },
                     "inResponseTo": {
                        "type": "string",
                        "index": "not_analyzed"
                     },
                     "responses": {
                        "properties": {
                           "at": {
                              "type": "string",
                              "index": "not_analyzed"
                           },
                           "body": {
                              "type": "string",
                              "fields": {
                                 "raw": {
                                    "type": "string",
                                    "index": "not_analyzed"
                                 }
                              }
                           },
                           "context": {
                              "type": "string",
                              "index": "not_analyzed"
                           },
                           "dateCreated": {
                              "type": "long"
                           },
                           "endTimeCode": {
                              "type": "long"
                           },
                           "id": {
                              "type": "string",
                              "index": "not_analyzed"
                           },
                           "inResponseTo": {
                              "type": "string",
                              "index": "not_analyzed"
                           },
                           "startTimeCode": {
                              "type": "long"
                           },
                           "user": {
                              "properties": {
                                 "email": {
                                    "type": "string",
                                    "index": "not_analyzed"
                                 },
                                 "firstName": {
                                    "type": "string",
                                    "index": "not_analyzed"
                                 },
                                 "id": {
                                    "type": "string",
                                    "index": "not_analyzed"
                                 },
                                 "lastName": {
                                    "type": "string",
                                    "index": "not_analyzed"
                                 },
                                 "userName": {
                                    "type": "string",
                                    "index": "not_analyzed"
                                 }
                              }
                           }
                        }
                     },
                     "startTimeCode": {
                        "type": "long"
                     },
                     "user": {
                        "properties": {
                           "email": {
                              "type": "string",
                              "index": "not_analyzed"
                           },
                           "firstName": {
                              "type": "string",
                              "index": "not_analyzed"
                           },
                           "id": {
                              "type": "string",
                              "index": "not_analyzed"
                           },
                           "lastName": {
                              "type": "string",
                              "index": "not_analyzed"
                           },
                           "userName": {
                              "type": "string",
                              "index": "not_analyzed"
                           }
                        }
                     }
                  }
               },
               "startTimeCode": {
                  "type": "long"
               },
               "user": {
                  "properties": {
                     "email": {
                        "type": "string",
                        "index": "not_analyzed"
                     },
                     "firstName": {
                        "type": "string",
                        "index": "not_analyzed"
                     },
                     "id": {
                        "type": "string",
                        "index": "not_analyzed"
                     },
                     "lastName": {
                        "type": "string",
                        "index": "not_analyzed"
                     },
                     "userName": {
                        "type": "string",
                        "index": "not_analyzed"
                     }
                  }
               }
            }
         },
         "asset": {
            "properties": {
               "_source": {
                  "properties": {
                     "excludes": {
                        "type": "string"
                     },
                     "includes": {
                        "type": "string"
                     }
                  }
               },
               "accountId": {
                  "type": "string",
                  "index": "not_analyzed"
               },
               "approvalStatus": {
                  "type": "string",
                  "index": "not_analyzed"
               },
               "archiveStatus": {
                  "type": "string",
                  "index": "not_analyzed"
               },
               "averageRating": {
                  "type": "long"
               },
               "commentCount": {
                  "type": "long"
               },
               "dateCreated": {
                  "type": "long"
               },
               "dateModified": {
                  "type": "long"
               },
               "derivatives": {
                  "properties": {
                     "duration": {
                        "type": "long"
                     },
                     "fileSize": {
                        "type": "long"
                     },
                     "height": {
                        "type": "long"
                     },
                     "posterFrame": {
                        "type": "string",
                        "index": "not_analyzed"
                     },
                     "progress": {
                        "type": "long"
                     },
                     "properties": {
                        "properties": {
                           "WebVTT": {
                              "type": "string"
                           },
                           "duration": {
                              "type": "long"
                           },
                           "height": {
                              "type": "long"
                           },
                           "url": {
                              "type": "string"
                           },
                           "webVTT": {
                              "type": "string"
                           },
                           "width": {
                              "type": "long"
                           }
                        }
                     },
                     "strategies": {
                        "properties": {
                           "streamer": {
                              "type": "string",
                              "index": "not_analyzed"
                           },
                           "type": {
                              "type": "string",
                              "index": "not_analyzed"
                           },
                           "url": {
                              "type": "string",
                              "index": "not_analyzed"
                           }
                        }
                     },
                     "thumbnail": {
                        "type": "string",
                        "index": "not_analyzed"
                     },
                     "type": {
                        "type": "string",
                        "index": "not_analyzed"
                     },
                     "url": {
                        "type": "string",
                        "index": "not_analyzed"
                     },
                     "width": {
                        "type": "long"
                     }
                  }
               },
               "description": {
                  "type": "string"
               },
               "duration": {
                  "type": "long"
               },
               "external": {
                  "type": "boolean"
               },
               "fileName": {
                 "type": "string",
                 "analyzer": "mediasilo_word_analyzer",
                 "fields": {
                    "raw": {
                       "type": "string",
                       "index": "not_analyzed"
                    }
                 }
               },
               "folderId": {
                  "type": "string",
                  "index": "not_analyzed"
               },
               "from": {
                  "type": "long"
               },
               "id": {
                  "type": "string",
                  "index": "not_analyzed"
               },
               "isExternal": {
                  "type": "boolean"
               },
               "isPrivate": {
                  "type": "boolean"
               },
               "myRating": {
                  "type": "double"
               },
               "posterFrame": {
                  "type": "string",
                  "index": "not_analyzed"
               },
               "private": {
                  "type": "boolean"
               },
               "progress": {
                  "type": "long"
               },
               "projectId": {
                  "type": "string",
                  "index": "not_analyzed"
               },
               "tags": {
                  "type": "string"
               },
               "title": {
                  "type": "string",
                  "analyzer": "mediasilo_word_analyzer",
                  "fields": {
                     "raw": {
                        "type": "string",
                        "index": "not_analyzed"
                     }
                  }
               },
               "transcriptStatus": {
                  "type": "string",
                  "index": "not_analyzed"
               },
               "type": {
                  "type": "string",
                  "index": "not_analyzed"
               },
               "uploadedBy": {
                  "type": "string",
                  "index": "not_analyzed"
               }
            }
         }
      },
      "settings": {
         "index": {
            "creation_date": "1428416729044",
            "uuid": "4f7ypiGLR_yn8M_Y5uII6w",
            "analysis": {
               "filter": {
                  "mediasilo_word_filter": {
                    "split_on_case_change":true,
                    "preserve_original": true,
                    "generate_word_parts":true,
                     "type": "word_delimiter"
                  }
               },
               "analyzer": {
                  "mediasilo_word_analyzer": {
                     "filter": [
                        "mediasilo_word_filter",
                        "lowercase",
                     ],
                     "tokenizer": "standard"
                  }
               }
            },
            "number_of_replicas": "1",
            "number_of_shards": "5",
            "version": {
               "created": "1040499"
            }
         }
      },
      "warmers": {}
   }'





# Install node and elasticsearch-reindex
curl -sL https://deb.nodesource.com/setup | sudo bash -
sudo apt-get install -y nodejs
npm install -g elasticsearch-reindex





# Move data from source index into target index
reindex_cmd="elasticsearch-reindex -f http://$source_host:9200/$source_index_name/asset -t http://$target_host:9200/$backup_index_name/asset"
log "Reindexing data:"
log "==================>Executing: $reindex_cmd"
eval $reindex_cmd





# Delete source index type
delete_old_index_type_cmd="curl -XDELETE \"http://$target_host:9200/$source_index_name/asset\""
log "Deleting old index type, asset:"
log "==================>Executing: $delete_old_index_type_cmd"
eval $delete_old_index_type_cmd




# Add analyzer to source index
log "Adding analyzer to source index"
curl -X POST "http://$target_host:9200/$source_index_name/_close"
curl -X PUT "http://$target_host:9200/$source_index_name/_settings" -d \
'{
    "analysis": {
        "filter": {
            "mediasilo_word_filter": {
                "type": "word_delimiter",
                "split_on_case_change":true,
                 "preserve_original": true,
                 "generate_word_parts":true
            }
        },
        "analyzer": {
            "mediasilo_word_analyzer": {
                "tokenizer": "standard",
                "filter": [
                    "mediasilo_word_filter",
                    "lowercase",
                ]
            }
        }
    }
}'
curl -X POST "http://$target_host:9200/$source_index_name/_open"





# Recreate source index type
log "Recreating old index type, asset with updated analyzer and mappings"
curl -X POST "http://$target_host:9200/$source_index_name/asset/_mapping" -d \
  '{
      "asset": {
              "properties": {
                 "_source": {
                    "properties": {
                       "excludes": {
                          "type": "string"
                       },
                       "includes": {
                          "type": "string"
                       }
                    }
                 },
                 "accountId": {
                    "type": "string",
                    "index": "not_analyzed"
                 },
                 "approvalStatus": {
                    "type": "string",
                    "index": "not_analyzed"
                 },
                 "archiveStatus": {
                    "type": "string",
                    "index": "not_analyzed"
                 },
                 "averageRating": {
                    "type": "long"
                 },
                 "commentCount": {
                    "type": "long"
                 },
                 "dateCreated": {
                    "type": "long"
                 },
                 "dateModified": {
                    "type": "long"
                 },
                 "derivatives": {
                    "properties": {
                       "duration": {
                          "type": "long"
                       },
                       "fileSize": {
                          "type": "long"
                       },
                       "height": {
                          "type": "long"
                       },
                       "posterFrame": {
                          "type": "string",
                          "index": "not_analyzed"
                       },
                       "progress": {
                          "type": "long"
                       },
                       "properties": {
                          "properties": {
                             "WebVTT": {
                                "type": "string"
                             },
                             "duration": {
                                "type": "long"
                             },
                             "height": {
                                "type": "long"
                             },
                             "url": {
                                "type": "string"
                             },
                             "webVTT": {
                                "type": "string"
                             },
                             "width": {
                                "type": "long"
                             }
                          }
                       },
                       "strategies": {
                          "properties": {
                             "streamer": {
                                "type": "string",
                                "index": "not_analyzed"
                             },
                             "type": {
                                "type": "string",
                                "index": "not_analyzed"
                             },
                             "url": {
                                "type": "string",
                                "index": "not_analyzed"
                             }
                          }
                       },
                       "thumbnail": {
                          "type": "string",
                          "index": "not_analyzed"
                       },
                       "type": {
                          "type": "string",
                          "index": "not_analyzed"
                       },
                       "url": {
                          "type": "string",
                          "index": "not_analyzed"
                       },
                       "width": {
                          "type": "long"
                       }
                    }
                 },
                 "description": {
                    "type": "string"
                 },
                 "duration": {
                    "type": "long"
                 },
                 "external": {
                    "type": "boolean"
                 },
                 "fileName": {
                   "type": "string",
                   "analyzer": "mediasilo_word_analyzer",
                   "fields": {
                      "raw": {
                         "type": "string",
                         "index": "not_analyzed"
                      }
                   }
                 },
                 "folderId": {
                    "type": "string",
                    "index": "not_analyzed"
                 },
                 "from": {
                    "type": "long"
                 },
                 "id": {
                    "type": "string",
                    "index": "not_analyzed"
                 },
                 "isExternal": {
                    "type": "boolean"
                 },
                 "isPrivate": {
                    "type": "boolean"
                 },
                 "myRating": {
                    "type": "double"
                 },
                 "posterFrame": {
                    "type": "string",
                    "index": "not_analyzed"
                 },
                 "private": {
                    "type": "boolean"
                 },
                 "progress": {
                    "type": "long"
                 },
                 "projectId": {
                    "type": "string",
                    "index": "not_analyzed"
                 },
                 "tags": {
                    "type": "string"
                 },
                 "title": {
                    "type": "string",
                    "analyzer": "mediasilo_word_analyzer",
                    "fields": {
                       "raw": {
                          "type": "string",
                          "index": "not_analyzed"
                       }
                    }
                 },
                 "transcriptStatus": {
                    "type": "string",
                    "index": "not_analyzed"
                 },
                 "type": {
                    "type": "string",
                    "index": "not_analyzed"
                 },
                 "uploadedBy": {
                    "type": "string",
                    "index": "not_analyzed"
                 }
              }
           }
        }
  }'




  # Move data from target backup index into target old index
  reindex_cmd="elasticsearch-reindex -f http://$target_host:9200/$backup_index_name/asset -t http://$target_host:9200/$source_index_name/asset"
  log "Reindexing data:"
  log "==================>Executing: $reindex_cmd"
  eval $reindex_cmd
