#ifndef TSX_H
#define TSX_H

void handle_sigill(int sig);
int try_xtest();
int try_transaction();
int is_rtm_visible();

#endif