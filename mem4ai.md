# Mem4ai


- constructor: Accept db path, LLM context windowes and other params we need
- load (session_id): Either load or create a new one
- add_memory(message:str, role:str <user|assistant>, metadata)
- build_context(user_query, max_tokens, ....) -> 
- search_memory(query, meta_data_filter, (start_time, end_time): We can use oone or mix of these parametersd
- 

There is this concept of "chunk_index", which refer to a chunk of consecutive messages, chunk_i is (user_i_1 -> assistant_i_1 > user_i_2 > assistant_i_2 >...> user_i_n > assistant_i_n ) that the timestamp of  user_i_1 if far after the assistant_i-1_n and the the timestamp of assistant_i_n is far behind the user_i+1_1.

We need to assign the chunk index in the add_memory function.

Please egnerate error free, elegant code, single file, handle all these. Please add any extra parameters or funciton that we definitly need and I forgot